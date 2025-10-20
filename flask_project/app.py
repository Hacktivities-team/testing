from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, Country, Category, Place, CurrencyRate 
import json 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sizin_cox_gizli_acar' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///countries.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# --- İDARƏETMƏ KONFİQURASİYASI ---
ADMIN_USERNAME = '123'
ADMIN_PASSWORD = '123' 
PLACE_TYPES = ['Place', 'Hotel', 'Restaurant', 'Hospital', 'Language', 'Safety'] 

with app.app_context():
    db.create_all()

# --- HELPER FUNKSİYASI: Admin Qoruması ---
def check_admin_auth():
    if not session.get('logged_in'):
        flash('Admin panelə daxil olmaq üçün giriş etməlisiniz.', 'warning')
        return redirect(url_for('login'))
    return None

# --- USER PANEL ROUTES ---

@app.route('/')
def index():
    all_categories = Category.query.all()
    is_logged_in = session.get('logged_in', False)
    return render_template('index.html', categories=all_categories, logged_in=is_logged_in)

# --- AUTHENTICATION ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Admin panelə xoş gəldiniz!', 'success')
            return redirect(url_for('admin_panel'))
        else:
            flash('Yanlış istifadəçi adı və ya parol!', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Uğurla çıxış etdiniz.', 'info')
    return redirect(url_for('index'))

# --- ADMIN PANEL ROUTES: Ölkə İdarəetməsi ---

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    auth_check = check_admin_auth()
    if auth_check: return auth_check
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        pin_lat = request.form.get('pin_lat', 0.0)
        pin_lon = request.form.get('pin_lon', 0.0)
        
        if not name or not code:
            flash('Zəhmət olmasa, bütün sahələri doldurun!', 'error')
            return redirect(url_for('admin_panel'))

        new_country = Country(name=name, code=code.upper(), pin_lat=pin_lat, pin_lon=pin_lon)
        try:
            db.session.add(new_country)
            db.session.commit()
            flash(f'{name} ölkəsi uğurla əlavə edildi!', 'success')
            return redirect(url_for('admin_panel'))
        except Exception:
            flash(f'Xəta: Ölkə əlavə edilmədi. Ola bilsin ki, adı və ya kodu artıq mövcuddur.', 'error')
            db.session.rollback()
            return redirect(url_for('admin_panel'))
    
    countries = Country.query.all()
    return render_template('admin.html', countries=countries)

@app.route('/admin/delete_country/<int:country_id>', methods=['POST'])
def delete_country(country_id):
    auth_check = check_admin_auth()
    if auth_check: return auth_check

    country_to_delete = Country.query.get_or_404(country_id)
    try:
        db.session.delete(country_to_delete)
        db.session.commit()
        flash(f'"{country_to_delete.name}" ölkəsi və onun bütün məlumatları uğurla silindi.', 'success')
    except Exception as e:
        flash(f'Silinmə zamanı xəta baş verdi: {e}', 'error')
        db.session.rollback()
        
    return redirect(url_for('admin_panel'))

# --- ADMIN PANEL ROUTES: Kateqoriya İdarəetməsi ---

@app.route('/admin/categories', methods=['GET', 'POST'])
def category_panel():
    auth_check = check_admin_auth()
    if auth_check: return auth_check

    if request.method == 'POST' and 'category_name' in request.form:
        cat_name = request.form.get('category_name')
        if cat_name:
            new_cat = Category(name=cat_name.strip().capitalize())
            try:
                db.session.add(new_cat)
                db.session.commit()
                flash(f'Kateqoriya "{cat_name}" uğurla əlavə edildi.', 'success')
            except Exception:
                flash('Xəta: Bu kateqoriya adı artıq mövcuddur.', 'error')
                db.session.rollback()
        return redirect(url_for('category_panel'))
    
    all_categories = Category.query.all()
    all_countries = Country.query.all()
    return render_template('admin_categories.html', categories=all_categories, countries=all_countries)


@app.route('/admin/delete_category/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    auth_check = check_admin_auth()
    if auth_check: return auth_check

    category_to_delete = Category.query.get_or_404(category_id)
    try:
        db.session.delete(category_to_delete)
        db.session.commit()
        flash(f'"{category_to_delete.name}" kateqoriyası uğurla silindi.', 'success')
    except Exception as e:
        flash(f'Silinmə zamanı xəta baş verdi: {e}', 'error')
        db.session.rollback()
        
    return redirect(url_for('category_panel'))


@app.route('/admin/assign_category', methods=['POST'])
def assign_category():
    # Bu funksiya BuildError xətasını aradan qaldırmaq üçün dəqiqləşdirilmiş addır
    auth_check = check_admin_auth()
    if auth_check: return auth_check

    country_id = request.form.get('country_id')
    category_id = request.form.get('category_id')
    country = Country.query.get(country_id)
    category = Category.query.get(category_id)

    if country and category:
        if category not in country.categories:
            country.categories.append(category)
            db.session.commit()
            flash(f'{country.name}-ə "{category.name}" kateqoriyası təyin edildi.', 'success')
        else:
            flash(f'{country.name} artıq "{category.name}" kateqoriyasına malikdir.', 'warning')
    else:
        flash('Xəta: Ölkə və ya Kateqoriya tapılmadı.', 'error')

    return redirect(url_for('category_panel'))

# --- ADMIN PANEL ROUTES: Kontent (Yerlər və Valyuta) İdarəetməsi ---

@app.route('/admin/content', methods=['GET', 'POST'])
def content_panel():
    auth_check = check_admin_auth()
    if auth_check: return auth_check
    
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        # 1. Yer Əlavə Etmə
        if form_type == 'add_place':
            country_id = request.form.get('country_id')
            place_type = request.form.get('place_type')
            name = request.form.get('name')
            
            new_place = Place(
                country_id=country_id,
                type=place_type,
                name=name,
                description=request.form.get('description'),
                rating=request.form.get('rating', 0.0),
                price_range=request.form.get('price_range'),
                tags=request.form.get('tags'),
                location_url=request.form.get('location_url'),
                menu_image_url=request.form.get('menu_image_url')
            )
            try:
                db.session.add(new_place)
                db.session.commit()
                flash(f'Yeni {place_type} "{name}" uğurla əlavə edildi!', 'success')
            except Exception as e:
                flash(f'Yer əlavə edilərkən xəta: {e}', 'error')
                db.session.rollback()
                
        # 2. Valyuta Məzənnəsi Əlavə Etmə/Yeniləmə
        elif form_type == 'add_rate':
            code = request.form.get('code').upper()
            rate = request.form.get('rate')
            
            existing_rate = CurrencyRate.query.filter_by(code=code).first()
            
            try:
                if existing_rate:
                    existing_rate.azn_rate = rate
                    flash(f'{code} məzənnəsi yeniləndi.', 'success')
                else:
                    new_rate = CurrencyRate(code=code, azn_rate=rate)
                    db.session.add(new_rate)
                    flash(f'Yeni valyuta {code} əlavə edildi.', 'success')
                db.session.commit()
            except Exception as e:
                flash(f'Valyuta əməliyyatı zamanı xəta: {e}', 'error')
                db.session.rollback()
        
        # 3. Yer Silmə
        elif form_type == 'delete_place':
            place_id = request.form.get('place_id')
            place_to_delete = Place.query.get(place_id)
            if place_to_delete:
                 try:
                    db.session.delete(place_to_delete)
                    db.session.commit()
                    flash(f'"{place_to_delete.name}" yaddaşdan silindi.', 'success')
                 except:
                    flash('Yer silinərkən xəta!', 'error')
                    db.session.rollback()
        
        return redirect(url_for('content_panel'))

    countries = Country.query.all()
    rates = CurrencyRate.query.all()
    places = Place.query.all()
    
    return render_template('admin_content.html', countries=countries, rates=rates, places=places, place_types=PLACE_TYPES)


# --- API ENDPOINTS (Front-end üçün) ---

@app.route('/api/countries', methods=['GET'])
def get_countries_api():
    """ Global Explorer üçün ölkələr siyahısını qaytarır. """
    countries = Country.query.all()
    country_list = [{
        'id': c.id, 
        'name': c.name, 
        'code': c.code,
        'lat': c.pin_lat, 
        'lon': c.pin_lon
    } for c in countries]
    return jsonify(country_list)

@app.route('/api/rates', methods=['GET'])
def get_rates_api():
    """ Valyuta konvertoru üçün məzənnələri qaytarır. """
    rates = CurrencyRate.query.all()
    rate_list = {'AZN': 1.0}
    for r in rates:
        rate_list[r.code] = float(r.azn_rate) 
    return jsonify(rate_list)

@app.route('/api/country/<string:country_code>/data', methods=['GET'])
def get_country_data(country_code):
    """ Ölkə səhifəsi (azerbaijan.html) üçün bütün yerləri qaytarır. """
    country = Country.query.filter_by(code=country_code.upper()).first_or_404()
    
    places = Place.query.filter_by(country_id=country.id).all()
    
    data = {
        'general': {
            'name': country.name,
            'capital': 'DB-də Paytaxt məlumatı yoxdur',
            'currency_code': 'AZN', 
            'timezone': 'UTC+4'
        },
        'places': [p.to_dict() for p in places if p.type == 'Place'],
        'hotels': [p.to_dict() for p in places if p.type == 'Hotel'],
        'restaurants': [p.to_dict() for p in places if p.type == 'Restaurant'],
        'hospitals': [p.to_dict() for p in places if p.type == 'Hospital'],
        'language': [p.to_dict() for p in places if p.type == 'Language'],
        'safety': [p.to_dict() for p in places if p.type == 'Safety']
    }
    
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)