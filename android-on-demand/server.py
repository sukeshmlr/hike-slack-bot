from flask import Flask, request, make_response, Response
from flaskext.mysql import MySQL
import os
import json
import pycurl
from threading import Thread
from slackclient import SlackClient


#enter slack_client token below
slack_client = SlackClient('<TOKEN_GOES_HERE>')
cwd=os.getcwd()

app = Flask(__name__)
mysql = MySQL()
#mysql db credentials
app.config['MYSQL_DATABASE_USER'] = '<USERNAME>'
app.config['MYSQL_DATABASE_PASSWORD'] = '<PASSWORD>'
app.config['MYSQL_DATABASE_DB'] = '<DB_NAME>'
app.config['MYSQL_DATABASE_HOST'] = '<DB_HOST_NAME'
mysql.init_app(app)

#Dictionaries for selected build options
build_dict={"rb": "Release Build","db": "Debug Build","ob": "Obfuscated build with debug true","bb": "Black build","ddb": "Debug build with DB access","rdb": "Release build with DB access","cdrb": "Custom end-point build for Docker Environment","ut": "Unit Test Report","ub": "Universal release build "}
task_dict ={0: "assembleArmRelease ",1: "assembleArmDebug ",2: "assembleArmObfuscated ",3: "assembleArmBlack ",4: "assembleCustomDevDebug ",5: "assembleCustomDevRelease ",6: "assemblecustomEndPointDebug ",7: "testArmRelease ",8: "assembleUniversalRelease",}                    

#Receptionist which sends 200 on recieving request and performs tasks on background.
@app.route("/action", methods=["POST"])
def receptionist():
    form_json = json.loads(request.form["payload"])
    thr = Thread(target=message_actions, args=[form_json])
    thr.start()
    return make_response("", 200)


#message action endpoint
def message_actions(form_json):
    with app.test_request_context('/action'):
        conn = mysql.connect()
        cur = conn.cursor()
        callback_id = form_json["callback_id"]
        if callback_id == "repo_selection":
            cur.execute(
                """DELETE from  
                slack_bot_android_on_demand where id=%s""", form_json["user"]["id"])
            conn.commit()
    
            if form_json["actions"][0]["value"]=="Fork":
                fork= True
            else:
                fork= False
            
            cur.execute(
                """INSERT INTO 
                slack_bot_android_on_demand (
                id,
                fork
                )
                VALUES (%s,%s)""", (form_json["user"]["id"],fork))
            conn.commit() 
        
            op= slack_client.api_call(
                "chat.update",
                ts=form_json["message_ts"],
                channel = form_json["channel"]['id'],
                text=" ",
                attachments=[]
                )
            if fork:
                open_dialog = slack_client.api_call(
                "dialog.open",
                trigger_id=form_json["trigger_id"],
                dialog={
                    "title": "Enter fork details",
                    "submit_label": "Submit",
                    "callback_id":  "branch_fork_selection",
                    "elements": [
                        {
                            "label": "Fork name",
                            "type": "text",
                            "name": "fork",
                            "placeholder": "Enter the fork name (if xxx/android-client enter xxx here)",
                            
                            
                        },  {"label": "branch name",
                            "type": "text",
                            "name": "branch",
                            "placeholder": "Enter the branch name here",
                            
                            
                        }]})
                
            else:
                open_dialog = slack_client.api_call(
                "dialog.open",
                trigger_id=form_json["trigger_id"],
                dialog={
                    "title": "Enter branch name",
                    "submit_label": "Submit",
                    "callback_id":  "branch_selection",
                    "elements": [
                        {
                            "label": "Enter Branch Name ",
                            "type": "text",
                            "name": "branch",
                            "placeholder": "Enter the branch name here"  
                            
                        }]})
                
        elif callback_id == "branch_fork_selection" or callback_id == "branch_selection":
            if callback_id=="branch_fork_selection":
                cur.execute(
                """UPDATE slack_bot_android_on_demand SET branch_name = %s, fork_name= %s WHERE id=%s""", (form_json["submission"]["branch"],form_json["submission"]["fork"], form_json["user"]["id"]))
                conn.commit()
            elif callback_id=="branch_selection":
                cur.execute(
                """UPDATE slack_bot_android_on_demand SET branch_name = %s WHERE id=%s""", (form_json["submission"]["branch"], form_json["user"]["id"]))
                conn.commit()
            attachments_json = [
                {
                "fallback": "Upgrade your Slack client to use messages like these.",
                "color": "#3AA3E3",
                "attachment_type": "default",
                "callback_id": "leak_canary",
                "actions": [
                    {
                        "name": "yes",
                        "text": "Yes",
                        "style":"primary",
                        "type": "button",
                        "value": "yes"
                    },
                    {
                        "name": "no",
                        "text": "No",
                        "type": "button",
                        "value": "no"
                    }
                ]
                }
                ]
            open_dialog = slack_client.api_call(
                "chat.postMessage",
                channel = form_json["channel"]['id'],
                text="Do you want to include leak canary in your build(s)?",
                attachments=attachments_json
            )
        elif callback_id == "leak_canary":
            if form_json["actions"][0]["value"]=="yes":
                cur.execute(
                """UPDATE slack_bot_android_on_demand SET leakcanary = 1 WHERE id=%s""", form_json["user"]["id"])
                conn.commit()
           
            attachments_json = [
                {
                    "fallback": "Upgrade your Slack client to use messages like these.",
                    "color": "#3AA3E3",
                    "attachment_type": "default",
                    "callback_id": "job_selection",
                    "actions": [
                        {
                        "name": "job_list",
                        "text": " ",
                        "type": "select",
                        "options": [
                            {
                                "text": "Release Build",
                                "value": "rb"
                            },
                            {
                                "text": "Debug build",
                                "value": "db"
                            },
                              {
                                "text": "Universal release build",
                                "value": "ub"
                            },
                            {
                                "text": "Obfuscated build with debug true",
                                "value": "ob"
                            },
                            {
                                "text": "Black build",
                                "value": "bb"
                            },
                            {
                                "text": "Debug build with DB Access",
                                "value": "ddb"
                            },
                            {
                                "text": "Release build with DB Access",
                                "value": "rdb"
                            },
                            {
                                "text": "Custom endpoint build for Docker environment",
                                "value": "cdrb"
                            },
                            {
                                "text": "Unit Test Report",
                                "value": "ut"
                            }
                        ] },
                        {
                            "name": "cancel",
                            "text": "Cancel Build",
                            "type": "button",
                            "style": "danger",
                            "value": "cancel",
                            "confirm": {
                             "title": "Are you sure?",
                             "text": "Do you really want to cancel the build generation?",
                            "ok_text": "Yes",
                             "dismiss_text": "No"
                            }
                        }
                    ]
                }
                ]
            open_dialog = slack_client.api_call(
            "chat.update",
            ts=form_json["message_ts"],
            channel = form_json["channel"]['id'],
            text="Which build(s) do you want to run?",
            attachments=attachments_json
            )
        elif callback_id=="job_selection":
            if form_json["actions"][0]["name"]=="cancel":
                op= slack_client.api_call(
                "chat.update",
                ts=form_json["message_ts"],
                channel = form_json["channel"]['id'],
                text="You have canceled the build successfully. Please use the /androidbuild command to generate new build. ",
                attachments=[]
                )
            if form_json["actions"][0]["name"]=="done":
                select_query = "select * from slack_bot_android_on_demand WHERE id='"+form_json["user"]["id"]+"'"
                cur.execute(select_query)
                data = cur.fetchall()
                tasks = " "
                builds=" "
                if data[0][4]==1:
                    builds=builds+build_dict["rb"]+", "
                    tasks = tasks + task_dict[0]
                if data[0][5]==1:
                    builds=builds+build_dict["db"]+", "
                    tasks = tasks + task_dict[1]
                if data[0][6]==1:
                    builds=builds+build_dict["ob"]+", "
                    tasks = tasks + task_dict[2]
                if data[0][7]==1:
                    builds=builds+build_dict["bb"]+", "
                    tasks = tasks + task_dict[3]
                if data[0][8]==1:
                    builds=builds+build_dict["ddb"]+", "
                    tasks = tasks + task_dict[4]
                if data[0][9]==1:
                    builds=builds+build_dict["rdb"]+", "
                    tasks = tasks + task_dict[5]
                if data[0][10]==1:
                    builds=builds+build_dict["cdrb"]+", "
                    tasks = tasks + task_dict[6]
                if data[0][11]==1:
                    builds=builds+build_dict["ut"]+", "
                    tasks = tasks + task_dict[7]
                if data[0][12]==1:
                    builds=builds+build_dict["ub"]+", "
                    tasks = tasks + task_dict[8]
                
                op= slack_client.api_call(
                "chat.update",
                ts=form_json["message_ts"],
                channel = form_json["channel"]['id'],
                text="You have selected the following builds: "+builds+"\n \n We will notify you once build is generated.",
                attachments=[]
                )
                fork_value="hike"
                if data[0][1]==1:
                    fork_value=data[0][2]
                c = pycurl.Curl()
                c.setopt(c.URL, 'https://circleci.com/api/v1.1/project/github/hike/android-client/tree/internal_release')
                c.setopt(c.POST, 1)
                if data[0][12]==1:
                    leak_canary_val="false"
                else:
                    leak_canary_val="true"
                send = [('config', (pycurl.FORM_FILE,cwd+"/config.yml")),('build_parameters[disableLeakCanary]',leak_canary_val),('build_parameters[branch]',data[0][3]),('build_parameters[USER_NUM]',data[0][0]),('build_parameters[fork]',fork_value),('build_parameters[tasks]',tasks)]
                c.setopt(c.USERPWD, "519563eecd133b317477be07d4b5a0f4223eae74")
                c.setopt(c.HTTPPOST,send)
                c.setopt(pycurl.HTTPHEADER, ['Accept-Language: en'])
                c.perform()
                
            else:
                query = "UPDATE slack_bot_android_on_demand SET "+form_json["actions"][0]["selected_options"][0]["value"]+"= 1 WHERE id='"+form_json["user"]["id"]+"'"
                cur.execute(query)
                conn.commit()
                select_query = "select * from slack_bot_android_on_demand WHERE id='"+form_json["user"]["id"]+"'"
                cur.execute(select_query)
                data = cur.fetchall()
                
                builds=" "
                if data[0][4]==1:
                    builds=builds+build_dict["rb"]+", "
                if data[0][5]==1:
                    builds=builds+build_dict["db"]+", "
                if data[0][6]==1:
                    builds=builds+build_dict["ob"]+", "
                if data[0][7]==1:
                    builds=builds+build_dict["bb"]+", "
                if data[0][8]==1:
                    builds=builds+build_dict["ddb"]+", "
                if data[0][9]==1:
                    builds=builds+build_dict["rdb"]+", "
                if data[0][10]==1:
                    builds=builds+build_dict["cdrb"]+", "
                if data[0][11]==1:
                    builds=builds+build_dict["ut"]+", "
                if data[0][12]==1:
                    builds=builds+build_dict["ub"]+", "
                
                builds=builds+ "\n"
                builds =builds + "\n\n Get the selected builds by clicking on \"Generate build\" button below."      
                attachments_json = [
                {
                    "fallback": "Upgrade your Slack client to use messages like these.",
                    "color": "#3AA3E3",
                    "text": "You have currently selected:"+builds,
                    "attachment_type": "default",
                    "callback_id": "job_selection",
                    "actions": [
                        
                        {
                            "name": "done",
                            "text": "Generate Build",
                            "type": "button",
                            "style": "primary",
                            "value": "done"
                        }
                    ]
                },
                {
                    "fallback": "Upgrade your Slack client to use messages like these.",
                    "color": "#3AA3E3",
                    "attachment_type": "default",
                    "text": " If you want to add more builds to the current selection below select build below.",
                    "callback_id": "job_selection",
                    "actions": [
                        {
                        "name": "job_list",
                        "text": " ",
                        "type": "select",
                        "options": [
                            {
                                "text": "Release Build",
                                "value": "rb"
                            },
                            {
                                "text": "Debug build",
                                "value": "db"
                            },
                              {
                                "text": "Universal release build",
                                "value": "ub"
                            },
                            {
                                "text": "Obfuscated build with debug true",
                                "value": "ob"
                            },
                            {
                                "text": "Black build",
                                "value": "bb"
                            },
                            {
                                "text": "Debug build with DB Access",
                                "value": "ddb"
                            },
                            {
                                "text": "Release build with DB Access",
                                "value": "rdb"
                            },
                            {
                                "text": "Custom endpoint build for Docker environment",
                                "value": "cdrb"
                            },
                            {
                                "text": "Unit Test Report",
                                "value": "ut"
                            }
                        ] },  {
                            "name": "cancel",
                            "text": "Cancel Build",
                            "type": "button",
                            "value": "cancel",
                            "style": "danger",
                            "confirm": {
                             "title": "Are you sure?",
                             "text": "Do you really want to cancel the build generation?",
                            "ok_text": "Yes",
                             "dismiss_text": "No"
                            }
                        }
                        ]
                }
                ]
                op = slack_client.api_call(
                "chat.update",
                ts=form_json["message_ts"],
                channel = form_json["channel"]['id'],
                text="Which build(s) do you want to run?",
                attachments=attachments_json
                )
        conn.close()        
    




@app.route("/", methods=["POST"])
def getandroidapk():
    data = request.form.to_dict()
    attachments_json = [
    {
        "fallback": "Upgrade your Slack client to use messages like these.",
        "color": "#3AA3E3",
        "attachment_type": "default",
        "callback_id": "repo_selection",
        "actions": [
             {
                "name": "Main",
                "text": "Main repository",
                "type": "button",
                "value": "Main"
            },
             {
                "name": "Fork",
                "text": "Forked repository",
                "type": "button",
                "value": "Fork"
            }
        ]
    }
    ]
    open_dialog = slack_client.api_call(
    "chat.postMessage",
    channel = data['channel_id'],
    text="Which repository do you want to use?",
    attachments=attachments_json
    )
    return make_response("", 200)

if __name__ == "__main__":
    app.run()