from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask import jsonify
from werkzeug.utils import secure_filename
import pandas as pd
import os
import json
from functools import wraps

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

app = Flask(__name__)
app.secret_key = "secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///election.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Cấu hình thư mục lưu trữ file danh sách
app.config['LIST_FOLDER'] = UPLOAD_FOLDER
# Cấu hình thư mục lưu trữ file văn kiện
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'txt', 'pptx'}

db = SQLAlchemy(app)

# Database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user' hoặc 'admin'

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    choice = db.Column(db.String(20), nullable=False)  # 'Agree' or 'Disagree'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Kiểm tra phần mở rộng của file
# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xls', 'xlsx'}

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            return render_template('error.html', message="You do not have permission to access this page."), 403
        return f(*args, **kwargs)
    return decorated_function

# Initialize database
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('vote'))
    return redirect(url_for('login'))

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         user = User.query.filter_by(username=username, password=password).first()
#         if user:
#             session['user_id'] = user.id
#             return redirect(url_for('vote'))
#         else:
#             return "Invalid username or password"
#     return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['role'] = user.role  # Lưu vai trò
            return redirect(url_for('admin_dashboard' if user.role == 'admin' else 'vote'))
        else:
            return "Invalid username or password"
    return render_template('login.html')

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         confirm_password = request.form['confirm_password']
        
#         if password != confirm_password:
#             return "Passwords do not match!"
        
#         if User.query.filter_by(username=username).first():
#             return "Username already exists!"
        
#         new_user = User(username=username, password=password)
#         db.session.add(new_user)
#         db.session.commit()
#         return redirect(url_for('login'))
#     return render_template('register.html')

@app.route('/09012004', methods=['GET', 'POST'])
#@admin_required
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']  # Nhận vai trò từ form

        if password != confirm_password:
            return "Passwords do not match!"

        if User.query.filter_by(username=username).first():
            return "Username already exists!"

        new_user = User(username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('view_users'))
    return render_template('register.html')

# @app.route('/import', methods=['GET', 'POST'])
# def import_excel():
#     if request.method == 'POST':
#         if 'file' not in request.files:
#             return "No file uploaded", 400

#         file = request.files['file']
#         if file.filename == '':
#             return "No file selected", 400

#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             file.save(filepath)

#             # Read the Excel file
#             try:
#                 data = pd.read_excel(filepath)
#                 for index, row in data.iterrows():
#                     # Assumes Excel columns: 'username' and 'password'
#                     username = row['username']
#                     password = row['password']

#                     if not User.query.filter_by(username=username).first():
#                         new_user = User(username=username, password=password)
#                         db.session.add(new_user)
#                 db.session.commit()
#             except Exception as e:
#                 return f"Error processing file: {e}", 500

#             return redirect(url_for('view_users'))  # Redirect to a page to view users
#     return render_template('import.html')

@app.route('/import', methods=['GET', 'POST'])
@admin_required  # Chỉ admin mới có quyền import
def import_excel():
    if request.method == 'POST':
        # Kiểm tra xem có file được tải lên không
        if 'file' not in request.files:
            flash("No file uploaded", "danger")
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash("No file selected", "danger")
            return redirect(request.url)

        # Kiểm tra định dạng file
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['LIST_FOLDER'], filename)
            file.save(filepath)

            try:
                # Đọc file Excel
                data = pd.read_excel(filepath)

                # Kiểm tra các cột cần thiết
                required_columns = {'username', 'password', 'role'}
                if not required_columns.issubset(data.columns):
                    flash("File is missing required columns: 'username', 'password', 'role'", "danger")
                    return redirect(request.url)

                # Thêm người dùng từ file Excel vào CSDL
                for index, row in data.iterrows():
                    username = row['username']
                    password = row['password']
                    role = row['role'].strip().lower()

                    # Kiểm tra giá trị hợp lệ của cột role
                    if role not in ['user', 'admin']:
                        flash(f"Invalid role '{role}' at row {index + 1}. Allowed values: 'user', 'admin'", "danger")
                        return redirect(request.url)

                    # Kiểm tra username đã tồn tại chưa
                    if not User.query.filter_by(username=username).first():
                        new_user = User(username=username, password=password, role=role)
                        db.session.add(new_user)
                db.session.commit()

                flash("User list imported successfully!", "success")
                return redirect(url_for('view_users'))

            except Exception as e:
                flash(f"Error processing file: {e}", "danger")
                return redirect(request.url)

        flash("Invalid file type. Please upload an Excel file (.xls, .xlsx)", "danger")
        return redirect(request.url)

    return render_template('import.html')

# @app.route('/vote', methods=['GET', 'POST'])
# def vote():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))

#     user_id = session['user_id']
#     if request.method == 'POST':
#         choice = request.form['choice']
#         if not Vote.query.filter_by(user_id=user_id).first():
#             new_vote = Vote(user_id=user_id, choice=choice)
#             db.session.add(new_vote)
#             db.session.commit()
#             return redirect(url_for('results'))
#         return "You have already voted!"
#     return render_template('vote.html')

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    # Nếu không phải là 'user', không cho phép hiệp thương
    if user.role != 'user':
        return "Phân quyền Admin không được hiệp thương.", 403

    if request.method == 'POST':
        choice = request.form['choice']
        if not Vote.query.filter_by(user_id=user_id).first():
            new_vote = Vote(user_id=user_id, choice=choice)
            db.session.add(new_vote)
            db.session.commit()
            return redirect(url_for('results'))
        return "You have already voted!"
    return render_template('vote.html')

@app.route('/results')
def results():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    total_votes = Vote.query.count()
    agree_votes = Vote.query.filter_by(choice='Agree').count()
    disagree_votes = Vote.query.filter_by(choice='Disagree').count()
    return render_template('results.html', total=total_votes, agree=agree_votes, disagree=disagree_votes)

@app.route('/api/results')
def api_results():
    total_votes = Vote.query.count()
    agree_votes = Vote.query.filter_by(choice='Agree').count()
    disagree_votes = Vote.query.filter_by(choice='Disagree').count()

    agree_percentage = (agree_votes / total_votes * 100) if total_votes > 0 else 0
    disagree_percentage = (disagree_votes / total_votes * 100) if total_votes > 0 else 0

    return jsonify({
        'total': total_votes,
        'agree': agree_votes,
        'disagree': disagree_votes,
        'agree_percentage': round(agree_percentage, 2),
        'disagree_percentage': round(disagree_percentage, 2)
    })

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Lấy tên văn kiện và file tải lên
        document_name = request.form['document_name']
        file = request.files['file']
        
        if file and allowed_file(file.filename):
            # Tạo tên file mới, sử dụng tên văn kiện nhập vào + phần mở rộng của file
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{document_name}.{file_extension}")
            
            # Lưu file vào thư mục uploads
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Chuyển hướng người dùng đến trang xem văn kiện
            return redirect(url_for('view_documents'))
    
    return render_template('upload.html')

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

#Xóa người dùng
@app.route('/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        return render_template('error.html', message="Bạn không có quyền xóa 1 admin khác!"), 403

    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('view_users'))

#Chỉnh sửa phân quyền
@app.route('/edit_role/<int:user_id>', methods=['POST'])
@admin_required
def edit_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin' and session['user_id'] != user.id:
        return render_template('error.html', message="Bạn không có quyền điều chỉnh thông tin này!"), 403

    new_role = request.form['role']
    if new_role not in ['user', 'admin']:
        return render_template('error.html', message="Invalid role provided!"), 400

    user.role = new_role
    db.session.commit()
    return redirect(url_for('view_users'))

@app.route('/view_documents')
def view_documents():
    # Lấy tất cả các file trong thư mục uploads
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('view_documents.html', files=files)

# @app.route('/users')
# def view_users():
#     users = User.query.all()
#     return render_template('users.html', users=users)
@app.route('/users')
@admin_required
def view_users():
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/live_results')
def live_results():
    return render_template('live_results.html')

@app.route('/home')
def index():
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)