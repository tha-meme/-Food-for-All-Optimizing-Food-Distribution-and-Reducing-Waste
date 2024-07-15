from flask import Flask,render_template,request,redirect,url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO
import seaborn as sns
import base64
import pandas as pd
from werkzeug.utils import secure_filename
import os
import threading


app=Flask(__name__)

UPLOAD_FOLDER = r'C:\Users\shrey\Desktop\DV_FLASK\static\uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = os.path.abspath(r'C:\Users\shrey\Desktop\DV_FLASK\static\uploads')
app.config['SQLALCHEMY_DATABASE_URI']="mysql+pymysql://root:123456@localhost/Foods"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY']="thishello"
db = SQLAlchemy(app)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/donate' , methods=['POST','GET'])
def donate():
    if request.method=='POST':
        fname = request.form['fname']
        quantity = request.form['quantity']
        location = request.form['location']
        phone = request.form['phone']
        donar = request.form['donar']
        shelf = request.form['shelf']
        dates = request.form['dates']

        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                db.session.execute(text("INSERT INTO donate (fname, quantity, shelf, donar, location, phone, dates, image) VALUES (:fname, :quantity, :shelf, :donar, :location, :phone, :dates, :image)"), {"fname": fname, "quantity": quantity, "shelf":shelf, "donar": donar, "location": location, "phone": phone, "dates": dates, "image": filename})
                db.session.execute(text("INSERT INTO display_donate (fname, quantity, shelf, donar, location, phone, dates, image) VALUES (:fname, :quantity, :shelf, :donar, :location, :phone, :dates, :image)"), {"fname": fname, "quantity": quantity, "shelf":shelf, "donar": donar, "location": location, "phone": phone, "dates": dates, "image": filename})
                db.session.execute(text("INSERT INTO donate_vizuals (fname, quantity, shelf, donar, location, phone, dates, image) VALUES (:fname, :quantity, :shelf, :donar, :location, :phone, :dates, :image)"), {"fname": fname, "quantity": quantity, "shelf":shelf, "donar": donar, "location": location, "phone": phone, "dates": dates, "image": filename})
                db.session.commit()
                print("Data committed to the database")     
    return render_template('donate.html')

# engine.connect()
@app.route('/receive',methods=['GET', 'POST'])
def receive():
    search_query = request.args.get('search', None)
    
    if search_query:
        query = db.session.execute(text("SELECT * FROM display_donate WHERE LOWER(fname) LIKE LOWER(:search_query) OR LOWER(location) LIKE LOWER(:search_query)"),{"search_query": f"%{search_query}%"})
    else:
        query = db.session.execute(text("SELECT * FROM display_donate"))

    return render_template('receive.html', query=query, search_query=search_query)

@app.route('/receive_form/<int:no>')
def receive_form(no):
    query = db.session.execute(text("SELECT fname FROM display_donate where id=:id"), {"id": no})
    result = query.fetchone()
    food_name = result[0]
    print(f"Received food name: {food_name}")
    return render_template('receive_form.html', id=no,food=food_name)


@app.route('/receive_success/<int:id>',methods=['GET', 'POST'])
def receive_success(id):
    if request.method=='GET':    
        query = db.session.execute(text("SELECT * FROM display_donate where id=:id"), {"id": id})
        result = query.fetchone()
        print(result)
        if result:
            fname = result[1]
            donar = result[4]
            quantity = result[2]
            shelf = result[3]
            location = result[5]
            phone = result[6]
            dates = result[7]
            db.session.execute(text("INSERT into receive(fname,quantity,shelf,donar,location,phone,dates) VALUES(:fname,:quantity,:shelf,:donar,:location,:phone, :dates)"), {"fname":fname,"quantity":quantity,"shelf":shelf,"donar":donar,"location":location,"phone":phone, "dates":dates})
            db.session.execute(text("DELETE FROM display_donate where id=:id"), {"id": id})
            db.session.commit()
            return render_template('home.html')
    return render_template('home.html')



lock = threading.Lock()


@app.route('/dashboard')
def dashboard():
    with lock:
        plt.style.use('dark_background')
    # Fetch donation data
        query_donate = db.session.execute(text("SELECT fname, SUM(quantity) FROM donate GROUP BY fname"))
        res_donate = query_donate.fetchall()
        df_donate = pd.DataFrame(res_donate, columns=["Food Type", "Total Quantity (Donated)"])

        # Fetch visualization data
        query_vizuals = db.session.execute(text("SELECT fname, SUM(quantity) FROM donate_vizuals GROUP BY fname"))
        res_vizuals = query_vizuals.fetchall()
        df_vizuals = pd.DataFrame(res_vizuals, columns=["Food Type", "Total Quantity (Vizuals)"])

        # Fetch received data
        query_receive = db.session.execute(text("SELECT fname, SUM(quantity) FROM receive GROUP BY fname"))
        res_receive = query_receive.fetchall()
        df_receive = pd.DataFrame(res_receive, columns=["Food Type", "Total Quantity (Received)"])

        # Create donation bar chart
        plt.figure(figsize=(5, 4))
        plt.bar(df_donate["Food Type"], df_donate["Total Quantity (Donated)"], width=0.8)
        plt.title("Donation Bar Chart")
        plt.xlabel("Food Type")
        plt.ylabel("Total Quantity (Donated)")
        plt.xticks(rotation=50, ha="right", rotation_mode="anchor", fontsize=6)
        plt.yticks(fontsize=6)
        plt.subplots_adjust(bottom=0.2)
        plt.tight_layout()
        img_donate = BytesIO()
        plt.savefig(img_donate, format='png')
        img_donate.seek(0)
        plt.close()

        # Create received bar chart
        plt.figure(figsize=(5, 4))
        plt.bar(df_receive["Food Type"], df_receive["Total Quantity (Received)"], width=0.8, color='#FF0000')
        plt.title("Received Bar Chart")
        plt.xlabel("Food Type")
        plt.ylabel("Total Quantity (Received)")
        plt.xticks(rotation=50, ha="right", rotation_mode="anchor", fontsize=6)
        plt.yticks(fontsize=6)
        plt.subplots_adjust(bottom=0.2)
        plt.tight_layout()
        img_receive = BytesIO()
        plt.savefig(img_receive, format='png')
        img_receive.seek(0)
        plt.close()

        # Create pie chart
        fig_pie, ax_pie = plt.subplots(figsize=(5,4))
        
        def func(pct, allvalues):
            absolute = round(float(pct)/100.*float(sum(allvalues)), 2)
            return f"{pct:.1f}%\n({absolute:.2f} kg)"


        ax_pie.pie(df_receive["Total Quantity (Received)"], labels=df_receive["Food Type"], autopct='%.1f%%', startangle=90)
        ax_pie.axis('equal') 

        # Save the pie chart to a BytesIO object
        img_pie = BytesIO()
        plt.savefig(img_pie, format='png')
        img_pie.seek(0)
        plt.close()

        # Create received pie chart
        fig_receive_pie, ax_receive_pie = plt.subplots(figsize=(5,4))
        
        def func(pct, allvalues):
            absolute = round(float(pct)/100.*float(sum(allvalues)), 2)
            return f"{pct:.1f}%\n({absolute:.2f} kg)"


        ax_receive_pie.pie(df_receive["Total Quantity (Received)"], labels=df_receive["Food Type"], autopct='%.1f%%', startangle=90)
        ax_receive_pie.axis('equal') 
        img_receive_pie = BytesIO()
        plt.savefig(img_receive_pie, format='png')
        img_receive_pie.seek(0)
        plt.close()

        # Create line plot for donation
        query_donate = db.session.execute(text("SELECT fname, quantity, dates FROM donate"))
        res_donate = query_donate.fetchall()

        df_donate = pd.DataFrame(res_donate, columns=["Food Type", "Quantity", "Dates"])

        # Extract day from dates
        df_donate['Day'] = pd.to_datetime(df_donate['Dates']).dt.day_name()

        df_donate['Quantity'] = pd.to_numeric(df_donate['Quantity'])

        # Create a new dataframe for the sum of quantities per day
        df_sum_per_day_donate = df_donate.groupby('Day')['Quantity'].sum().reset_index()

        # Sort the days in the correct order
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        df_sum_per_day_donate['Day'] = pd.Categorical(df_sum_per_day_donate['Day'], categories=days_order, ordered=True)
        df_sum_per_day_donate = df_sum_per_day_donate.sort_values('Day')

        fig_line_donation, ax_line_donation = plt.subplots(figsize=(6, 4))
        ax_line_donation.plot(df_sum_per_day_donate['Day'], df_sum_per_day_donate['Quantity'], marker='o', linestyle='-', color='orange', markerfacecolor='cyan')
        ax_line_donation.set_xlabel('Day')
        ax_line_donation.set_ylabel('Total Quantity')
        ax_line_donation.set_title('Total Quantity per Day - Donation')
        ax_line_donation.grid(True)
        img_line_donation = BytesIO()
        plt.savefig(img_line_donation, format='png')
        img_line_donation.seek(0)
        plt.close()

        # Fetch receiving data
        query_receive = db.session.execute(text("SELECT fname, quantity, dates FROM receive"))
        res_receive = query_receive.fetchall()
        df_receive = pd.DataFrame(res_receive, columns=["Food Type", "Quantity", "Dates"])

        # Extract day from dates
        df_receive['Day'] = pd.to_datetime(df_receive['Dates']).dt.day_name()

        df_receive['Quantity'] = pd.to_numeric(df_receive['Quantity'])

        # Create a new dataframe for the sum of quantities per day for receiving
        df_sum_per_day_receive = df_receive.groupby('Day')['Quantity'].sum().reset_index()
        df_sum_per_day_receive['Day'] = pd.Categorical(df_sum_per_day_receive['Day'], categories=days_order, ordered=True)
        df_sum_per_day_receive = df_sum_per_day_receive.sort_values('Day')

        # Create bar chart for receiving
        plt.figure(figsize=(5, 5))
        plt.bar(df_sum_per_day_receive['Day'], df_sum_per_day_receive['Quantity'], color='cyan')
        plt.xlabel('Day')
        plt.ylabel('Total Quantity')
        plt.title('Total Quantity per Day - Receiving')
        plt.xticks(rotation=45, ha="right", rotation_mode="anchor", fontsize=8)
        plt.yticks(fontsize=8)
        plt.tight_layout()
        img_bar_receive = BytesIO()
        plt.savefig(img_bar_receive, format='png')
        img_bar_receive.seek(0)
        plt.close()
        
         # Create heatmap for donation
        pivot_donate = df_donate.pivot_table(index='Day', columns='Food Type', values='Quantity', aggfunc='sum')
        plt.figure(figsize=(5, 4))
        sns.heatmap(pivot_donate, cmap='viridis', annot=True, fmt='g', linewidths=.5)
        plt.title('Quantity vs Day - Donation')
        plt.xlabel('Food Type')
        plt.ylabel('Day')
        img_heatmap_donate = BytesIO()
        plt.savefig(img_heatmap_donate, format='png')
        img_heatmap_donate.seek(0)
        plt.close()

        # Create heatmap for receiving
        pivot_receive = df_receive.pivot_table(index='Day', columns='Food Type', values='Quantity', aggfunc='sum')
        plt.figure(figsize=(5, 4))
        sns.heatmap(pivot_receive, cmap='viridis', annot=True, fmt='g', linewidths=.5)
        plt.title('Quantity vs Day - Receiving')
        plt.xlabel('Food Type')
        plt.ylabel('Day')
        img_heatmap_receive = BytesIO()
        plt.savefig(img_heatmap_receive, format='png')
        img_heatmap_receive.seek(0)
        plt.close()

        # Embed all charts in the HTML template
        chart_url_donate = base64.b64encode(img_donate.getvalue()).decode('utf8')
        chart_url_receive = base64.b64encode(img_receive.getvalue()).decode('utf8')
        chart_url_pie = base64.b64encode(img_pie.getvalue()).decode('utf8')
        chart_url_receive_pie = base64.b64encode(img_receive_pie.getvalue()).decode('utf8')
        chart_url_line_donation = base64.b64encode(img_line_donation.getvalue()).decode('utf8')
        chart_url_bar_receive = base64.b64encode(img_bar_receive.getvalue()).decode('utf8')
        chart_url_heatmap_donate = base64.b64encode(img_heatmap_donate.getvalue()).decode('utf8')
        chart_url_heatmap_receive = base64.b64encode(img_heatmap_receive.getvalue()).decode('utf8')

        return render_template('dashboard.html', 
                            chart_url_donate=chart_url_donate, 
                            chart_url_receive=chart_url_receive, 
                            chart_url_pie=chart_url_pie,
                            chart_url_receive_pie=chart_url_receive_pie,
                            chart_url_line_donation=chart_url_line_donation,
                            chart_url_bar_receive=chart_url_bar_receive,
                            chart_url_heatmap_donate=chart_url_heatmap_donate,
                            chart_url_heatmap_receive=chart_url_heatmap_receive)


    


if __name__=="__main__":
    app.run(debug=True, use_reloader=False)



    #  use_reloader=False