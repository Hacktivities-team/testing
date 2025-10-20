from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Çoxdan-Çoxa Əlaqə Cədvəli (Ölkə & Kateqoriya)
country_category = db.Table('country_category',
    db.Column('country_id', db.Integer, db.ForeignKey('country.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

class Country(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(3), unique=True, nullable=False) 
    # API üçün lazım olan koordinatlar
    pin_lat = db.Column(db.Float, default=0.0)
    pin_lon = db.Column(db.Float, default=0.0)

    categories = db.relationship('Category', secondary=country_category, lazy='subquery',
                                 backref=db.backref('countries', lazy=True))
    places = db.relationship('Place', backref='country', lazy='dynamic', cascade="all, delete-orphan") # Ölkə silinəndə yerləri də silir

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

class Place(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # Məsələn: 'Place', 'Hotel', 'Restaurant', 'Hospital'
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    rating = db.Column(db.Float, default=0.0)
    price_range = db.Column(db.String(50)) # Məsələn: '$$', '$$$'
    tags = db.Column(db.String(255)) # Məsələn: 'Historical, Museum'
    location_url = db.Column(db.String(500)) # Google Maps linki
    menu_image_url = db.Column(db.String(500)) # Menyu/Detal Modalı üçün şəkil linki

    def to_dict(self):
        # API üçün JSON-a çevirmə funksiyası
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'rating': self.rating,
            'price_range': self.price_range,
            'tags': self.tags.split(',') if self.tags else [],
            'location_url': self.location_url,
            'menu_image_url': self.menu_image_url,
            'country_code': self.country.code if self.country else None
        }

class CurrencyRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), unique=True, nullable=False) # Məsələn: USD, EUR, TRY
    azn_rate = db.Column(db.Float, nullable=False) # 1 X = AZN ilə nə qədərdir (Statik)

    def to_dict(self):
        return {
            'code': self.code,
            'rate_to_azn': self.azn_rate
        }