import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import joblib

# Model için sütunlar
features = ['energy_100g', 'fat_100g', 'sugars_100g', 'fiber_100g', 'proteins_100g', 'salt_100g']
target = 'nutriscore_grade'

filename = 'en.openfoodfacts.org.products.csv'
chunksize = 100000

X_list = []
y_list = []

# chunksize ile satır hatalarını yoksayarak oku
for chunk in pd.read_csv(filename, sep='\t', chunksize=chunksize, low_memory=False, on_bad_lines='skip'):
    if all(col in chunk.columns for col in features + [target]):
        temp = chunk[features + [target]].dropna()
        X_list.append(temp[features])
        y_list.append(temp[target])

# Tüm verileri birleştir
X = pd.concat(X_list, ignore_index=True)
y = pd.concat(y_list, ignore_index=True)

# Eğitim ve test kümeleri
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Model oluştur ve eğit
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Modeli kaydet
joblib.dump(model, 'nutriscore_model.pkl')
print("✅ Model başarıyla eğitildi ve kaydedildi.")
