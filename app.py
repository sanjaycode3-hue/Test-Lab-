from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import send_file

import mysql.connector
import pandas as pd

import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

from reportlab.platypus import SimpleDocTemplate
from reportlab.platypus import Table
from reportlab.platypus.tables import TableStyle

from reportlab.lib import colors

app = Flask(__name__)

# MYSQL CONNECTION

db = mysql.connector.connect(

    host="localhost",
    user="root",
    password="sanjay",
    database="test_lab"

)

cursor = db.cursor()

# HOME

@app.route('/')
def home():

    search = request.args.get('search')

    if search:

        cursor.execute("""

        SELECT *
        FROM machine_records

        WHERE machine_name LIKE %s

        OR customer_name LIKE %s

        ORDER BY sno DESC

        """, (f'%{search}%', f'%{search}%'))

    else:

        cursor.execute("""

        SELECT *
        FROM machine_records
        ORDER BY sno DESC

        """)

    records = cursor.fetchall()

    # TOTAL CYCLES

    cursor.execute("""

    SELECT SUM(cycle_count)
    FROM machine_records

    """)

    total_cycles = cursor.fetchone()[0]

    if total_cycles is None:
        total_cycles = 0

    # RUNNING COUNT

    cursor.execute("""

    SELECT COUNT(*)
    FROM machine_records

    WHERE machine_status='RUNNING'

    """)

    running_count = cursor.fetchone()[0]

    # STOPPED COUNT

    cursor.execute("""

    SELECT COUNT(*)
    FROM machine_records

    WHERE machine_status='STOPPED'

    """)

    stopped_count = cursor.fetchone()[0]

    # MAINTENANCE COUNT

    cursor.execute("""

    SELECT COUNT(*)
    FROM machine_records

    WHERE machine_status='MAINTENANCE'

    """)

    maintenance_count = cursor.fetchone()[0]

    return render_template(

        "index.html",

        records=records,

        total_cycles=total_cycles,

        running_count=running_count,

        stopped_count=stopped_count,

        maintenance_count=maintenance_count

    )

# SAVE RECORD

@app.route('/save', methods=['POST'])
def save():

    machine_name = request.form['machine_name']
    subject_name = request.form['subject_name']
    customer_name = request.form['customer_name']
    reason_for_running = request.form['reason_for_running']
    shift_name = request.form['shift_name']
    person_name = request.form['person_name']
    cycle_count = request.form['cycle_count']
    machine_status = request.form['machine_status']

    sql = """

    INSERT INTO machine_records

    (

    machine_name,
    subject_name,
    customer_name,
    reason_for_running,
    shift_name,
    person_name,
    cycle_count,
    machine_status

    )

    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)

    """

    values = (

        machine_name,
        subject_name,
        customer_name,
        reason_for_running,
        shift_name,
        person_name,
        cycle_count,
        machine_status

    )

    cursor.execute(sql, values)

    db.commit()

    return redirect('/')

# PDF REPORT

@app.route('/pdf')
def pdf():

    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    shift_name = request.args.get('shift_name')

    if shift_name:

        cursor.execute("""

        SELECT *
        FROM machine_records

        WHERE DATE(created_at)
        BETWEEN %s AND %s

        AND shift_name=%s

        ORDER BY sno DESC

        """, (from_date, to_date, shift_name))

    else:

        cursor.execute("""

        SELECT *
        FROM machine_records

        WHERE DATE(created_at)
        BETWEEN %s AND %s

        ORDER BY sno DESC

        """, (from_date, to_date))

    data = cursor.fetchall()

    pdf_file = "reports/Machine_Report.pdf"

    document = SimpleDocTemplate(pdf_file)

    table_data = []

    headings = [

        "SNO",
        "Machine",
        "Subject",
        "Customer",
        "Reason",
        "Shift",
        "Person",
        "Cycles",
        "Status",
        "Time"

    ]

    table_data.append(headings)

    for row in data:

        table_data.append(list(row))

    table = Table(table_data)

    style = TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),

        ('TEXTCOLOR', (0,0), (-1,0), colors.white),

        ('GRID', (0,0), (-1,-1), 1, colors.black),

        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')

    ])

    table.setStyle(style)

    elements = []

    elements.append(table)

    document.build(elements)

    return send_file(

        pdf_file,
        as_attachment=True

    )

# EXCEL EXPORT

@app.route('/excel')
def excel():

    cursor.execute("""

    SELECT *
    FROM machine_records
    ORDER BY sno DESC

    """)

    data = cursor.fetchall()

    columns = [

        "SNO",
        "Machine",
        "Subject",
        "Customer",
        "Reason",
        "Shift",
        "Person",
        "Cycles",
        "Status",
        "Time"

    ]

    df = pd.DataFrame(data, columns=columns)

    excel_file = "reports/machine_report.xlsx"

    df.to_excel(

        excel_file,
        index=False

    )

    return send_file(

        excel_file,
        as_attachment=True

    )

# EMAIL REPORT

@app.route('/email_report')
def email_report():

    import smtplib

    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    pdf_file = "reports/Machine_Report.pdf"

    # One sender only
    sender_email = "sanjaycode3@gmail.com"

    sender_password = "qwertyuiopasdfgghh"

    # Multiple receivers allowed
    receiver_emails = [

        "sj4275117@gmail.com"

    ]

    message = MIMEMultipart()

    message['From'] = sender_email

    message['To'] = ", ".join(receiver_emails)

    message['Subject'] = "Machine Production Report"

    body = """

    Product Engineering Test Lab

    Daily production report attached.

    """

    message.attach(MIMEText(body, 'plain'))

    attachment = open(pdf_file, "rb")

    part = MIMEBase('application', 'octet-stream')

    part.set_payload(attachment.read())

    encoders.encode_base64(part)

    part.add_header(

        'Content-Disposition',
        'attachment; filename=Machine_Report.pdf'

    )

    message.attach(part)

    server = smtplib.SMTP(

        'smtp.gmail.com',
        587

    )

    server.starttls()

    server.login(

        sender_email,
        sender_password

    )

    text = message.as_string()

    server.sendmail(

        sender_email,
        receiver_emails,
        text

    )

    server.quit()

    return "EMAIL SENT SUCCESSFULLY"

# RUN

if __name__ == '__main__':

    app.run(

        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True

    )