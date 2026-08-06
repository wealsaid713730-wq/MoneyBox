import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
import arabic_reshaper
from bidi.algorithm import get_display

FIREBASE_URL = "https://moneybox-b9e88-default-rtdb.firebaseio.com/"

def fix_text(text):
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        lbl = Label(text=fix_text("اختر اسم المستخدم للدخول"), font_size=24)
        btn_wael = Button(text=fix_text("تسجيل دخول باسم: وائل"), font_size=20, on_press=lambda x: self.login("وائل"))
        btn_abdo = Button(text=fix_text("تسجيل دخول باسم: عبد الرحمن"), font_size=20, on_press=lambda x: self.login("عبد الرحمن"))
        
        layout.add_widget(lbl)
        layout.add_widget(btn_wael)
        layout.add_widget(btn_abdo)
        self.add_widget(layout)

    def login(self, username):
        app = App.get_running_app()
        app.current_user = username
        self.manager.current = 'main'

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.main_layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        self.lbl_user = Label(text="", font_size=18, size_hint_y=None, height=30)
        self.lbl_total = Label(text=fix_text("إجمالي الصندوق المؤكد: 0 جنيه"), font_size=20, size_hint_y=None, height=40)
        
        self.amount_input = TextInput(hint_text=fix_text("المبلغ"), input_filter='float', multiline=False, size_hint_y=None, height=40)
        self.date_input = TextInput(hint_text=fix_text("التاريخ (YYYY-MM-DD)"), multiline=False, size_hint_y=None, height=40)
        
        btn_submit = Button(text=fix_text("إرسال عملية جديدة للتأكيد"), font_size=18, size_hint_y=None, height=45, on_press=self.submit_payment)
        btn_refresh = Button(text=fix_text("تحديث البيانات"), font_size=18, size_hint_y=None, height=45, on_press=self.update_ui)
        
        lbl_pending_title = Label(text=fix_text("عمليات تنتظر تأكيدك:"), font_size=18, size_hint_y=None, height=30)
        
        # قائمة العمليات المعلقة
        self.scroll = ScrollView()
        self.pending_grid = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.pending_grid.bind(minimum_height=self.pending_grid.setter('height'))
        self.scroll.add_widget(self.pending_grid)
        
        self.main_layout.add_widget(self.lbl_user)
        self.main_layout.add_widget(self.lbl_total)
        self.main_layout.add_widget(self.amount_input)
        self.main_layout.add_widget(self.date_input)
        self.main_layout.add_widget(btn_submit)
        self.main_layout.add_widget(btn_refresh)
        self.main_layout.add_widget(lbl_pending_title)
        self.main_layout.add_widget(self.scroll)
        
        self.add_widget(self.main_layout)

    def on_enter(self):
        app = App.get_running_app()
        self.lbl_user.text = fix_text(f"المستخدم الحالي: {app.current_user}")
        self.update_ui()

    def submit_payment(self, instance):
        app = App.get_running_app()
        amount = self.amount_input.text
        date = self.date_input.text
        
        if not amount or not date:
            return
            
        new_data = {
            "payer": app.current_user,
            "amount": float(amount),
            "date": date,
            "status": "Pending"
        }
        
        requests.post(f"{FIREBASE_URL}/transactions.json", json=new_data)
        self.amount_input.text = ""
        self.date_input.text = ""
        self.update_ui()

    def update_ui(self, *args):
        app = App.get_running_app()
        self.pending_grid.clear_widgets()
        
        try:
            res = requests.get(f"{FIREBASE_URL}/transactions.json").json()
            total = 0
            if res:
                for key, val in res.items():
                    # احتساب الإجمالي للعمليات المؤكدة فقط
                    if val.get('status') == 'Approved':
                        total += val.get('amount', 0)
                    
                    # عرض العمليات التي تخص الطرف الآخر لتأكيدها
                    elif val.get('status') == 'Pending' and val.get('payer') != app.current_user:
                        txt = f"{val.get('payer')}: {val.get('amount')} ج - {val.get('date')}"
                        box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
                        lbl = Label(text=fix_text(txt), font_size=16)
                        btn_approve = Button(text=fix_text("تأكيد"), size_hint_x=0.3, on_press=lambda x, k=key: self.approve_transaction(k))
                        box.add_widget(lbl)
                        box.add_widget(btn_approve)
                        self.pending_grid.add_widget(box)
                        
            self.lbl_total.text = fix_text(f"إجمالي الصندوق المؤكد: {total} جنيه")
        except Exception:
            pass

    def approve_transaction(self, trans_id):
        app = App.get_running_app()
        update_data = {
            "status": "Approved",
            "confirmed_by": app.current_user
        }
        requests.patch(f"{FIREBASE_URL}/transactions/{trans_id}.json", json=update_data)
        self.update_ui()

class MoneyApp(App):
    current_user = ""
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == '__main__':
    MoneyApp().run()
