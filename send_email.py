import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pretty_html_table import build_table
import os


def send_email(results, receivers, subject = None) :

    # Specify the email contents
    mail = MIMEMultipart()
    html = """\
    <html><head></head><body>{0}</body></html>
    """.format(build_table(results, 'grey_light', text_align = 'right', font_family = 'arial', font_size = 10))
    # width_dict = ['100','200','200','100','100','100','100']
    mail.attach(MIMEText(html, 'html'))

    # Set my email address and the password key
    my_mail = 'martinbog19@gmail.com'
    if os.getenv("GITHUB_ACTIONS") == "true" :
        os.getenv('GMAIL_APP_KEY')
    else :
        with open('secrets/gmail_app_key.txt') as f:
            app_password = f.read()
    # Set the subject of the email
    mail['Subject'] = subject

    # Send the email using Gmail's SMTP server
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade connection to secure
            server.login(my_mail, app_password)  # Login with app password
            server.sendmail(my_mail, receivers, mail.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")