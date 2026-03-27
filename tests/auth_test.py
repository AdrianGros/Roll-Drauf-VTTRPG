import requests
base='http://127.0.0.1:5000'

def run():
    session = requests.Session()
    r1 = session.post(base+'/api/auth/register', json={'username':'testuser','email':'test@example.com','password':'SecurePass123!'})
    print('register', r1.status_code, r1.text)
    r2 = session.post(base+'/api/auth/login', json={'username':'testuser','password':'SecurePass123!'})
    print('login', r2.status_code, r2.text)
    r3 = session.get(base+'/api/auth/me')
    print('me', r3.status_code, r3.text)

if __name__ == '__main__':
    run()
