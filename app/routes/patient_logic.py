from flask import Blueprint,render_template,redirect,request,url_for,session
from datetime import date,timedelta,datetime
import sqlite3,os,json

patient_logic_bp=Blueprint("patient_logic",__name__)




@patient_logic_bp.route('/patient_login',methods=['POST','GET'])
def login_check():
    if(request.method=="POST"):
        un=request.form.get('username')
        pw=request.form.get('password')
        
        db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
        connection= sqlite3.connect(db_path)
        cursor=connection.cursor()

        checklogin="SELECT patient_id from patient WHERE username=? AND password=?"
        cursor.execute(checklogin,(un,pw))
        logintrue=cursor.fetchall()

        if(un==""):
           return render_template('patient_login.html',error="Username Field Required")
        if(pw==""):
           return render_template('patient_login.html',error="Password Field Required")
        
        if (logintrue):
            session['patient_id']=logintrue[0][0]
            return redirect(url_for('patient_logic.department_getter')) 

        else:
            return render_template('patient_login.html',error="Invalid credentials")
    return render_template('patient_login.html')





@patient_logic_bp.route('/patient_register',methods=['POST','GET'])
def register_check():
    if(request.method=="POST"):
        n=request.form.get('name')
        a=request.form.get('age')
        g=request.form.get('gender')
        ph=request.form.get('phone')
        un=request.form.get('username')
        pw=request.form.get('password')
        cpw=request.form.get('confirm_password')

        db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
        connection= sqlite3.connect(db_path)
        cursor=connection.cursor()

        check="SELECT 1 FROM patient WHERE phone=?"
        cursor.execute(check,(ph,))
        phcheck=cursor.fetchone()

        if(phcheck != None):
            return render_template('patient_register.html',error="Phone Number already registered")
        
        check="SELECT 1 FROM patient WHERE username=?"
        cursor.execute(check,(un,))
        uncheck=cursor.fetchone()

        if(uncheck != None):
            return render_template('patient_register.html',error="Username already taken")
        if (pw!=cpw):
            return render_template('patient_register.html',error="Password and Confirm Password does not match")
        if(len(pw)<8):
            return render_template('patient_register.html',error="Password must be atleast 8 characters")
        if(len(ph)!=10):
            return render_template('patient_register.html',error="Invalid Phone Number")        
        if(un==""):
           return render_template('patient_register.html',error="Username Field Required")
        if(pw==""):
           return render_template('patient_register.html',error="Password Field Required")
        
        register="INSERT INTO patient(username,password,name,age,gender,phone,is_active) VALUES(?,?,?,?,?,?,?)"
        cursor.execute(register,(un,pw,n,a,g,ph,1))
        connection.commit()

        return redirect(url_for('patient_logic.department_getter'))     
    return render_template('patient_register.html')





@patient_logic_bp.route("/patient_dashboard")
def department_getter():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
    connection= sqlite3.connect(db_path)
    cursor=connection.cursor()

    command_dept="""SELECT d.department_name, d.department_id, COUNT(doc.doctor_id) as doctors_count
    FROM department d
    LEFT JOIN doctor doc ON doc.department_id = d.department_id AND doc.is_active = 1
    GROUP BY d.department_id, d.department_name"""
    cursor.execute(command_dept)
    departments=cursor.fetchall()
    return render_template("patient_dashboard.html",departments=departments)




@patient_logic_bp.route("/patient_dashboard/department",methods=["POST","GET"])
def department_doctors():
    
    if (request.method=="POST"):
        slot=request.form.get("slot")
        c_type=request.form.get("c_type")
        if (slot and c_type):
            return redirect(url_for('patient_logic.appointment_booking',avai_id=slot,c_type=c_type))
        
    dept_id=request.args.get('dept_id',type=int)
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
    connection= sqlite3.connect(db_path)
    cursor=connection.cursor()

    command_dept_name="SELECT department_name FROM department WHERE department_id=?"
    cursor.execute(command_dept_name,(dept_id,))
    dept_name_row=cursor.fetchone()
    dept_name=dept_name_row[0]

    command_doctors="""SELECT d.doctor_id,d.name,d.basic_time_slot,d.follow_up,d.normal_consultancy,d.procedure,a.day,a.start_time,a.end_time,a.availability_id
    FROM doctor d JOIN doctor_availability a ON d.doctor_id=a.doctor_id
    WHERE d.department_id=? AND d.is_active=?
    ORDER BY d.doctor_id"""
    cursor.execute(command_doctors,(dept_id,1))
    rows=cursor.fetchall()

    doctors = {}
    for doc_id, doc_name, bts, follow,normal,procedure,day, start, end,avai_id in rows:
        if doc_id not in doctors:
            doctors[doc_id] = {
                "name": doc_name,
                "availability": {},
                "duration":[follow*bts,normal*bts,procedure*bts]   
            }
        if day not in doctors[doc_id]["availability"]:
            doctors[doc_id]["availability"][day] = {}
        doctors[doc_id]["availability"][day][avai_id]=f"{start}-{end}"

    return render_template("patient_dashboard_department.html",doctors=doctors,dept_name=dept_name)




@patient_logic_bp.route("/patient_dashboard/doctor_profile")
def doctor_profile():
    doc_id=request.args.get('doc_id',type=int)
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
    connection= sqlite3.connect(db_path)
    cursor=connection.cursor()

    command_doctor_profile="SELECT * FROM doctor WHERE doctor_id=?"
    cursor.execute(command_doctor_profile,(doc_id,))
    rows=cursor.fetchone()

    return render_template("patient_dashboard_doctor_profile.html",details=rows)




@patient_logic_bp.route("/patient_dashboard/my_profile")
def my_profile():
    patient_id = session.get('patient_id')

    db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    command_my_profile="SELECT name,age,gender,phone FROM patient WHERE patient_id=?"
    cursor.execute(command_my_profile,(session.get('patient_id'),))
    details=cursor.fetchone()

    command_my_appointments="""SELECT d.name,dept.department_name,a.date,a.start_time,a.end_time,t.medicine,t.notes,a.appointment_id 
    FROM appointment a 
    JOIN doctor d ON a.doctor_id=d.doctor_id 
    JOIN department dept ON d.department_id=dept.department_id
    LEFT JOIN treatment t ON a.appointment_id=t.appointment_id
    WHERE a.patient_id=?"""
    cursor.execute(command_my_appointments,(session.get('patient_id'),))
    app=cursor.fetchall()

    print("Session patient_id:", session.get('patient_id'))
    cursor.execute("SELECT * FROM appointment")
    print("All appointments:", cursor.fetchall())

    return render_template("patient_dashboard_myprofile.html",details=details,app=app)




@patient_logic_bp.route('/patient_dashboard/edit_profile',methods=['POST','GET'])
def edit_profile():
    if(request.method=="POST"):
        db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
        connection= sqlite3.connect(db_path)
        cursor=connection.cursor()

        name=request.form.get('name')
        age=request.form.get('age')
        gender=request.form.get('gender')
        phone=request.form.get('phone')

        command_edit_pofile="""UPDATE patient
        SET name=?,age=?,gender=?,phone=?
        WHERE patient_id=?"""
        cursor.execute(command_edit_pofile,(name,age,gender,phone,session.get('patient_id')))
        connection.commit()
        
        return redirect(url_for('patient_logic.my_profile'))
    
    
    return render_template('patient_dashboard_edit_profile.html')




@patient_logic_bp.route('/patient_dashboard/change_password',methods=['POST','GET'])
def change_password():
    if(request.method=="POST"):
        db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
        connection= sqlite3.connect(db_path)
        cursor=connection.cursor()

        opw=request.form.get('opw')
        npw=request.form.get('npw')
        cnpw=request.form.get('cnpw')
        
        command_check_opw="SELECT password from patient WHERE patient_id=?"
        cursor.execute(command_check_opw,(session.get('patient_id'),))
        old_pw=cursor.fetchone()

        if(opw!=old_pw[0]):
             return render_template("patient_dashboard_change_password.html",error="Old Password Wrong")
        if (npw!=cnpw):
            return render_template("patient_dashboard_change_password.html",error="Password and Confirm Password does not match")
        if(len(npw)<8):
            return render_template("patient_dashboard_change_password.html",error="Password should be atleast 8 characters")
      
        command_edit_pofile="""UPDATE patient
        SET password=?
        WHERE patient_id=?"""
        cursor.execute(command_edit_pofile,(npw,session.get('patient_id'),))
        connection.commit()
        
        return redirect(url_for('patient_logic.my_profile'))
    
    
    return render_template('patient_dashboard_change_password.html')




@patient_logic_bp.route("/patient_dashboard/appointment_booking", methods=["POST",'GET'])
def appointment_booking():

    if (request.method=="POST"):
        # Each radio value is an exact pre-computed slot (start_time to end_time)
        dic=json.loads(request.form.get("free_slots"))
        time=dic['start_time']+" to "+dic["end_time"]
        return redirect(url_for("patient_logic.confirm_appointment_details",avai_id=dic['avai_id'],date=dic['date'],time=time,c_type=dic['c_type']))


    avai_id=request.args.get('avai_id',type=int)
    c_type=request.args.get('c_type')
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
    connection= sqlite3.connect(db_path)
    cursor=connection.cursor()

    command_day="SELECT day FROM doctor_availability WHERE availability_id=?"
    cursor.execute(command_day,(avai_id,))
    day=cursor.fetchone()[0].lower()

    day_code={"monday":0,"tuesday":1,"wednesday":2,"thursday":3,
              "friday":4,"saturday":5,"sunday":6}

    today=date.today()
    days_between=(day_code[day]-today.weekday())%7
    first=today+timedelta(days=days_between)
    four_days=[]
    for i in range(4):
        dat=first+timedelta(weeks=i)
        parts=str(dat).split("-")
        parts=parts[::-1]
        four_days.append("-".join(parts))

    command_docname="""SELECT d.name,d.doctor_id
    FROM doctor d JOIN doctor_availability a
    ON d.doctor_id=a.doctor_id
    WHERE a.availability_id=?"""
    cursor.execute(command_docname,(avai_id,))
    docname=cursor.fetchone()

    command_dept="""SELECT dept.department_name
    FROM department dept JOIN doctor d JOIN doctor_availability a
    ON d.doctor_id=a.doctor_id AND dept.department_id=d.department_id
    WHERE a.availability_id=?"""
    cursor.execute(command_dept,(avai_id,))
    deptname=cursor.fetchone()

    command_time="SELECT basic_time_slot,follow_up,normal_consultancy,procedure FROM doctor WHERE doctor_id=?"
    cursor.execute(command_time,(docname[1],))
    time_row=cursor.fetchone()

    command_slot="SELECT day,start_time,end_time FROM doctor_availability WHERE availability_id=?"
    cursor.execute(command_slot,(avai_id,))
    slot=cursor.fetchone()

    bts          = time_row[0]                   # basic time slot in minutes
    slots_needed = time_row[int(c_type)]          # number of bts units needed for this consultation type
    duration     = bts * slots_needed             # total minutes for the appointment

    fmt="%H:%M"
    avail_start=datetime.strptime(slot[1],fmt)
    avail_end  =datetime.strptime(slot[2],fmt)

    # Total number of basic-time-slot buckets in this availability window
    total_minutes=int((avail_end-avail_start).total_seconds()//60)
    total_bts_count=total_minutes//bts

    # Fetch ALL booked (active) appointments for this doctor on the upcoming dates
    command_booked="""SELECT date,start_time,end_time
    FROM appointment
    WHERE doctor_id=(SELECT doctor_id FROM doctor_availability WHERE availability_id=?)
    AND status!=0"""
    cursor.execute(command_booked,(avai_id,))
    booked_all=cursor.fetchall()
    connection.close()

    all_slots=[]
    for day_date in four_days:
        # Build a boolean grid: True=free, False=blocked
        grid=[True]*total_bts_count

        for bk_date,bk_start,bk_end in booked_all:
            if bk_date!=day_date:
                continue
            bk_s=datetime.strptime(bk_start,fmt)
            bk_e=datetime.strptime(bk_end,fmt)
            # Only block slots that fall within THIS availability window
            offset_start=int((bk_s-avail_start).total_seconds()//60)
            offset_end  =int((bk_e-avail_start).total_seconds()//60)
            idx_start=max(0,offset_start//bts)
            idx_end  =min(total_bts_count,(offset_end+bts-1)//bts)  # ceiling division
            for idx in range(idx_start,idx_end):
                grid[idx]=False

        # Find every starting index where slots_needed consecutive free slots exist
        day_bookable=[]
        for idx in range(total_bts_count-slots_needed+1):
            if all(grid[idx:idx+slots_needed]):
                slot_start_dt=avail_start+timedelta(minutes=idx*bts)
                slot_end_dt  =slot_start_dt+timedelta(minutes=duration)
                day_bookable.append([slot_start_dt.strftime(fmt),slot_end_dt.strftime(fmt)])

        all_slots.append(day_bookable)

    slots1=all_slots[0]
    slots2=all_slots[1]
    slots3=all_slots[2]
    slots4=all_slots[3]

    return render_template('patient_dashboard_appointment_booking.html',time=time_row,avai_id=avai_id,date=four_days,doctor=docname,department=deptname,c_type=c_type,duration=duration,slot=slot,slots1=slots1,slots2=slots2,slots3=slots3,slots4=slots4)





@patient_logic_bp.route("/patient_dashboard/final_booking",methods=["POST"])
def appointment_final():
    if (request.method=="POST"):
        date=request.args.get('date')
        c_type=request.args.get('c_type')
        duration=request.args.get('duration')
        avai_id=request.args.get('avai_id')
        start=request.form.get('start_time')

        start_time=datetime.strptime(start,"%H:%M")
        end=(start_time+timedelta(minutes=int(duration))).strftime("%H:%M")
        time=start+" to "+end
        return redirect(url_for("patient_logic.confirm_appointment_details",avai_id=avai_id,date=date,time=time,c_type=c_type))
        




@patient_logic_bp.route("/patient_dashboard/confirm_appointment_details")
def confirm_appointment_details():
    avai_id=request.args.get('avai_id')
    date=request.args.get('date')
    time=request.args.get('time')
    c_type=request.args.get('c_type')

    if(c_type=="1"):
        consultation="Follow-up"
    elif(c_type=="2"):
        consultation="Normal Consultancy"
    elif(c_type=="3"):
        consultation="Procedure"

    db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
    connection= sqlite3.connect(db_path)
    cursor=connection.cursor()

    command_get_doctor="""SELECT d.doctor_id,d.name,dept.department_name
    FROM doctor d JOIN doctor_availability a ON a.doctor_id=d.doctor_id
    JOIN department dept  ON dept.department_id=d.department_id"""
    cursor.execute(command_get_doctor)
    doctor=cursor.fetchone()

    return render_template("patient_dashboard_confirm_appointment_details.html",doctor=doctor,time=time,consult=consultation,date=date)




@patient_logic_bp.route("/patient_dashboard/appointment_confirmed",methods=['POST'])
def appointment_confirmed():
    if(request.method=="POST"):
        db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        doctor_id = request.form.get("doctor_id")
        date      = request.form.get("date")
        time      = request.form.get("time")
        avai_id   = request.form.get("avai_id")
        consult=request.form.get("consult")

        times=time.split(" to ")
        new_start = datetime.strptime(times[0], "%H:%M")
        new_end   = datetime.strptime(times[1], "%H:%M")

        # Conflict check: fetch all active appointments for this doctor on the same date
        command_check_conflicts = """SELECT start_time, end_time FROM appointment
        WHERE doctor_id=? AND date=? AND status != 0"""
        cursor.execute(command_check_conflicts, (doctor_id, date))
        existing_appointments = cursor.fetchall()

        fmt = "%H:%M"
        conflict = False
        for appt in existing_appointments:
            booked_start = datetime.strptime(appt[0], fmt)
            booked_end   = datetime.strptime(appt[1], fmt)
            # No overlap means: new_end <= booked_start OR new_start >= booked_end
            if not (new_end <= booked_start or new_start >= booked_end):
                conflict = True
                break

        if conflict:
            cursor.execute("""SELECT d.doctor_id, d.name, dept.department_name
                FROM doctor d JOIN doctor_availability a ON a.doctor_id=d.doctor_id
                JOIN department dept ON dept.department_id=d.department_id
                WHERE a.availability_id=?""", (avai_id,))
            doctor = cursor.fetchone()
            connection.close()
            return render_template('patient_dashboard_confirm_appointment_details.html',
                                   doctor=doctor, time=time, consult=consult, date=date,
                                   error="This time slot is no longer available. The doctor already has an appointment during this period. Please go back and choose a different slot.")

        command_appointment_booked="""INSERT INTO appointment(doctor_id,patient_id,date,start_time,end_time,status,availability_id,consultancy_type) 
        VALUES(?,?,?,?,?,?,?,?) """
        cursor.execute(command_appointment_booked,(doctor_id,session.get('patient_id'),date,times[0],times[1],1,avai_id,consult))
        connection.commit()

        appointment_id = cursor.lastrowid
        connection.close()

        return render_template('patient_dashboard_appointment_details.html',appid=appointment_id)
    
@patient_logic_bp.route("/patient_dashboard/search_doc",methods=['POST'])
def search_doc_by_name():
        if (request.method=="POST"):
            db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()

            docname=request.form.get("doc_name")

            command_doctor_profile="SELECT * FROM doctor WHERE name=?"
            cursor.execute(command_doctor_profile,(docname,))
            rows=cursor.fetchall()

            return render_template("patient_dashboard_search_doctor_profile.html",details=rows)
        

