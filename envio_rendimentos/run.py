import subprocess

if __name__ == '__main__':
    subprocess.run(['python', 'manage.py', 'migrate'])
    subprocess.run(['python', 'manage.py', 'runserver', '0.0.0.0:8000'])
