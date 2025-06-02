import pandas as pd
import numpy as np
import re
import json
import logging
from typing import Dict, List, Optional, Union

# Logging konfigürasyonu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OpenFoodFactsPreprocessor:
    """
    OpenFoodFacts TSV dosyalarını projenin gereksinimlerine göre önişleme sınıfı
    """
    
    def __init__(self):
        # Proje için gerekli sütunları tanımla
        self.required_columns = {
            # Temel ürün bilgileri
            'basic_info': [
                'code', 'product_name', 'generic_name', 'brands', 'categories',
                'categories_en', 'main_category', 'main_category_en', 'quantity'
            ],
            
            # Besin değerleri (100g başına)
            'nutrition': [
                'energy_100g', 'fat_100g', 'saturated-fat_100g', 'trans-fat_100g',
                'carbohydrates_100g', 'sugars_100g', 'fiber_100g', 'proteins_100g',
                'salt_100g', 'sodium_100g'
            ],
            
            # Vitaminler ve mineraller
            'vitamins_minerals': [
                'vitamin-a_100g', 'vitamin-c_100g', 'vitamin-d_100g', 'vitamin-e_100g',
                'calcium_100g', 'iron_100g', 'potassium_100g', 'magnesium_100g', 'zinc_100g'
            ],
            
            # Alerjen ve güvenlik bilgileri
            'allergens_safety': [
                'allergens', 'allergens_en', 'traces', 'traces_en', 
                'additives_n', 'additives', 'additives_tags', 'additives_en'
            ],
            
            # Skorlar ve değerlendirmeler
            'scores': [
                'nutrition_grade_fr', 'nutrition_grade_uk', 'nutrition-score-fr_100g',
                'nutrition-score-uk_100g'
            ],
            
            # İçerik bilgileri
            'ingredients': [
                'ingredients_text', 'ingredients_from_palm_oil_n',
                'ingredients_that_may_be_from_palm_oil_n'
            ]
        }
        
        # Tüm gerekli sütunları birleştir
        self.all_required_columns = []
        for category in self.required_columns.values():
            self.all_required_columns.extend(category)
    
    def load_tsv(self, file_path: str, nrows: Optional[int] = None) -> pd.DataFrame:
        """
        TSV dosyasını güvenli şekilde yükle
        """
        try:
            logger.info(f"TSV dosyası yükleniyor: {file_path}")
            
            # Farklı encoding'ler dene
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(
                        file_path,
                        sep='\t',
                        encoding=encoding,
                        low_memory=False,
                        nrows=nrows,
                        dtype=str  # Tüm sütunları string olarak oku
                    )
                    logger.info(f"Dosya {encoding} encoding ile başarıyla yüklendi")
                    logger.info(f"Toplam satır sayısı: {len(df)}")
                    logger.info(f"Toplam sütun sayısı: {len(df.columns)}")
                    return df
                except UnicodeDecodeError:
                    continue
            
            raise ValueError("Hiçbir encoding ile dosya okunamadı")
            
        except Exception as e:
            logger.error(f"Dosya yükleme hatası: {e}")
            raise
    
    def check_available_columns(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Mevcut sütunları kontrol et ve eksik olanları belirle
        """
        available_columns = df.columns.tolist()
        missing_columns = []
        present_columns = []
        
        for col in self.all_required_columns:
            if col in available_columns:
                present_columns.append(col)
            else:
                missing_columns.append(col)
        
        logger.info(f"Mevcut gerekli sütunlar: {len(present_columns)}")
        logger.info(f"Eksik sütunlar: {len(missing_columns)}")
        
        if missing_columns:
            logger.warning(f"Eksik sütunlar: {missing_columns}")
        
        return {
            'present': present_columns,
            'missing': missing_columns,
            'all_available': available_columns
        }
    
    def clean_numeric_columns(self, df: pd.DataFrame, numeric_columns: List[str]) -> pd.DataFrame:
        """
        Sayısal sütunları temizle ve dönüştür
        """
        df_clean = df.copy()
        
        for col in numeric_columns:
            if col in df_clean.columns:
                # String değerleri sayısal değerlere dönüştür
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
                
                # Negatif değerleri NaN yap (besin değerleri negatif olamaz)
                df_clean.loc[df_clean[col] < 0, col] = np.nan
                
                # Aşırı yüksek değerleri kontrol et (outlier detection)
                if col.endswith('_100g') and col != 'energy_100g':
                    # Enerji dışındaki besin değerleri için 100g'dan fazla olamaz kuralı
                    df_clean.loc[df_clean[col] > 100, col] = np.nan
        
        return df_clean
    
    def process_allergens(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Alerjen bilgilerini işle ve standardize et
        """
        df_processed = df.copy()
        
        # Alerjen sütunlarını işle
        allergen_columns = ['allergens', 'allergens_en', 'traces', 'traces_en']
        
        for col in allergen_columns:
            if col in df_processed.columns:
                # Küçük harfe çevir ve standardize et
                df_processed[col] = df_processed[col].astype(str).str.lower()
                
                # 'nan' string'lerini gerçek NaN'a çevir
                df_processed[col] = df_processed[col].replace('nan', np.nan)
                
                # Boş string'leri NaN'a çevir
                df_processed[col] = df_processed[col].replace(['', ' '], np.nan)
        
        return df_processed
    
    def process_additives(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Katkı maddesi bilgilerini işle
        """
        df_processed = df.copy()
        
        # Katkı maddesi sayısını sayısal değere çevir
        if 'additives_n' in df_processed.columns:
            df_processed['additives_n'] = pd.to_numeric(
                df_processed['additives_n'], errors='coerce'
            )
            # Negatif değerleri 0 yap
            df_processed['additives_n'] = df_processed['additives_n'].clip(lower=0)
        
        return df_processed
    
    def calculate_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Türetilmiş özellikler hesapla (proje gereksinimlerine göre)
        """
        df_enhanced = df.copy()
        
        # Makro besin oranlarını hesapla
        numeric_cols = ['fat_100g', 'carbohydrates_100g', 'proteins_100g']
        if all(col in df_enhanced.columns for col in numeric_cols):
            total_macros = df_enhanced[numeric_cols].sum(axis=1)
            
            # Sıfır bölme hatasını önle
            total_macros = total_macros.replace(0, np.nan)
            
            df_enhanced['fat_ratio'] = df_enhanced['fat_100g'] / total_macros
            df_enhanced['carb_ratio'] = df_enhanced['carbohydrates_100g'] / total_macros
            df_enhanced['protein_ratio'] = df_enhanced['proteins_100g'] / total_macros
        
        # Sodyum/Potasyum oranı (hipertansiyon kontrolü için)
        if 'sodium_100g' in df_enhanced.columns and 'potassium_100g' in df_enhanced.columns:
            df_enhanced['sodium_potassium_ratio'] = (
                df_enhanced['sodium_100g'] / df_enhanced['potassium_100g'].replace(0, np.nan)
            )
        
        # Şeker yoğunluğu (diyabet kontrolü için)
        if 'sugars_100g' in df_enhanced.columns and 'carbohydrates_100g' in df_enhanced.columns:
            df_enhanced['sugar_intensity'] = (
                df_enhanced['sugars_100g'] / df_enhanced['carbohydrates_100g'].replace(0, np.nan)
            )
        
        # NOVA skoru tahmini (işlenmişlik düzeyi)
        df_enhanced['estimated_processing_level'] = self.estimate_processing_level(df_enhanced)
        
        return df_enhanced
    
    def estimate_processing_level(self, df: pd.DataFrame) -> pd.Series:
        """
        Katkı maddesi sayısına göre işlenmişlik düzeyini tahmin et
        """
        processing_level = pd.Series(1, index=df.index)  # Varsayılan: minimal işlenmiş
        
        if 'additives_n' in df.columns:
            additives = df['additives_n'].fillna(0)
            
            # Katkı maddesi sayısına göre sınıflandır
            processing_level.loc[additives == 0] = 1  # Minimal/işlenmemiş
            processing_level.loc[(additives > 0) & (additives <= 2)] = 2  # İşlenmiş
            processing_level.loc[(additives > 2) & (additives <= 5)] = 3  # Yüksek işlenmiş
            processing_level.loc[additives > 5] = 4  # Ultra işlenmiş
        
        return processing_level
    
    def apply_quality_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Veri kalitesi filtrelerini uygula (daha esnek)
        """
        initial_count = len(df)
        
        # Temel filtreler
        filtered_df = df.copy()
        
        # 1. Ürün adı olması gerekli
        filtered_df = filtered_df.dropna(subset=['product_name'])
        
        # 2. En az bir temel besin değeri olması gerekli
        basic_nutrition = ['energy_100g', 'fat_100g', 'carbohydrates_100g', 'proteins_100g']
        nutrition_mask = filtered_df[basic_nutrition].notna().any(axis=1)
        filtered_df = filtered_df[nutrition_mask]
        
        # 3. Aşırı eksik veri olan satırları filtrele (tüm sütunların %80'i eksik olanlar)
        missing_ratio = filtered_df.isnull().sum(axis=1) / len(filtered_df.columns)
        filtered_df = filtered_df[missing_ratio < 0.8]
        
        final_count = len(filtered_df)
        logger.info(f"Kalite filtreleri uygulandı: {initial_count} -> {final_count} ({final_count/initial_count*100:.1f}%)")
        
        return filtered_df
    
    def preprocess(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        sample_size: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Ana önişleme fonksiyonu
        """
        logger.info("OpenFoodFacts veri önişleme başlatılıyor...")
        
        # 1. Veri yükleme
        df = self.load_tsv(file_path, nrows=sample_size)
        
        # 2. Sütun kontrolü
        column_info = self.check_available_columns(df)
        
        # 3. Sadece mevcut gerekli sütunları seç
        available_required_cols = column_info['present']
        df_selected = df[available_required_cols].copy()
        
        # 4. Sayısal sütunları temizle
        numeric_columns = [col for col in available_required_cols 
                          if col.endswith('_100g') or col == 'additives_n']
        df_cleaned = self.clean_numeric_columns(df_selected, numeric_columns)
        
        # 5. Alerjen bilgilerini işle
        df_processed = self.process_allergens(df_cleaned)
        
        # 6. Katkı maddelerini işle
        df_processed = self.process_additives(df_processed)
        
        # 7. Türetilmiş özellikler hesapla
        df_enhanced = self.calculate_derived_features(df_processed)
        
        # 8. Kalite filtrelerini uygula
        df_final = self.apply_quality_filters(df_enhanced)
        
        # 9. Sonuçları kaydet
        if output_path:
            df_final.to_csv(output_path, index=False, encoding='utf-8')
            logger.info(f"İşlenmiş veri kaydedildi: {output_path}")
        
        # 10. Özet bilgiler
        self.print_summary(df_final)
        
        return df_final
    
    def print_summary(self, df: pd.DataFrame):
        """
        İşlenmiş verinin özetini yazdır
        """
        logger.info("=== VERİ ÖNİŞLEME ÖZETİ ===")
        logger.info(f"Toplam satır sayısı: {len(df)}")
        logger.info(f"Toplam sütun sayısı: {len(df.columns)}")
        
        # Eksik veri oranları
        missing_ratios = df.isnull().sum() / len(df) * 100
        high_missing = missing_ratios[missing_ratios > 50]
        
        if len(high_missing) > 0:
            logger.warning(f"Yüksek eksik veri oranına sahip sütunlar:")
            for col, ratio in high_missing.items():
                logger.warning(f"  {col}: {ratio:.1f}%")
        
        # Temel istatistikler
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) > 0:
            logger.info(f"Sayısal sütun sayısı: {len(numeric_columns)}")


# Kullanım örneği
if __name__ == "__main__":
    # Preprocessor'ı başlat
    preprocessor = OpenFoodFactsPreprocessor()
    
    # Veri önişleme işlemini çalıştır
    try:
        # Örnek kullanım - dosya yolunu ve çıktı yolunu belirtin
        input_file = "openfoodfacts_data.tsv"  # TSV dosyasının yolu
        output_file = "processed_openfoodfacts.csv"  # İşlenmiş verinin kaydedileceği yer
        
        # İlk 10000 satırla test et (tüm veri için None yapın)
        processed_df = preprocessor.preprocess(
            file_path=input_file,
            output_path=output_file,
            sample_size=10000  # Test için, tüm veri için None
        )
        
        print("\nVeri önişleme tamamlandı!")
        print(f"İşlenmiş veri boyutu: {processed_df.shape}")
        
    except FileNotFoundError:
        print("TSV dosyası bulunamadı. Lütfen dosya yolunu kontrol edin.")
    except Exception as e:
        print(f"Bir hata oluştu: {e}")