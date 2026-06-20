from dotenv import load_dotenv
load_dotenv()
from app.db.firestore import FirestoreService, init_firestore
import json

init_firestore()
db = FirestoreService().db
if db:
    uid = '3VkPsZP7tNbRZEKaZ4liMgeYps62'
    u_doc = db.collection('users').document(uid).get()
    print('User doc exists:', u_doc.exists)
    if u_doc.exists:
        print('User doc careerGoal:', u_doc.to_dict().get('careerGoal'))
        
    s_doc = db.collection('user_state').document(uid).get()
    print('State doc exists:', s_doc.exists)
    if s_doc.exists:
        print('State doc targetRole:', json.dumps(s_doc.to_dict().get('targetRole'), indent=2))
else:
    print('No DB connection')
