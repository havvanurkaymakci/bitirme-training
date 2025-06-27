import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../styles/ProductSearch.css';

function ProductSearch() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState({
    max_energy_kcal: '',
    min_energy_kcal: '',
    max_sugar: '',
    max_fat: '',
    max_saturated_fat: '',
    max_salt: '',
    max_sodium: '',
    min_fiber: '',
    min_proteins: '',
    max_proteins: '',
    exclude_ingredients: '',
    include_ingredients: '',
    is_vegan: false,
    is_vegetarian: false,
    nutriscore_grade: '',
    nova_group: '',
    additives: '',
    categories: [],
  });

  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const buildQueryParams = () => {
    const params = new URLSearchParams();
    params.append('query', query);

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== '' && value !== false && value !== null) {
        if (Array.isArray(value)) {
          if (value.length > 0) {
            params.append(key, value.join(','));
          }
        } else {
          params.append(key, value);
        }
      }
    });

    return params.toString();
  };

  const splitIntoChunks = (arr, chunkSize) => {
    const chunks = [];
    for (let i = 0; i < arr.length; i += chunkSize) {
      chunks.push(arr.slice(i, i + chunkSize));
    }
    return chunks;
  };

  const handleSearch = async () => {
    if (query.trim() === '') {
      setError('Lütfen bir ürün adı girin.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const queryParams = buildQueryParams();
      const response = await axios.get(`http://localhost:8000/api/products/product-search/?${queryParams}`);
      
      if (response.data && response.data.products && response.data.products.length > 0) {
        setProducts(response.data.products);
      } else {
        setError('Ürün bulunamadı.');
      }

    } catch (err) {
      setError('Veri alınırken hata oluştu.');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFilters((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

 const handleProductClick = (product) => {
  // Ürün ID'sini veya barcode'unu al
  const productId = product.id || product._id || product.code || product.barcode;
  
  if (productId) {
    // URL parametresi ile yönlendir
    navigate(`/product-detail/${productId}`);
  } else {
    console.error('Ürün ID bulunamadı:', product);
    setError('Ürün detayına gidilemedi: ID bulunamadı');
  }
};

  const getFilterDescription = () => {
    const messages = [];

    if (filters.max_energy_kcal) messages.push(`Enerji ${filters.max_energy_kcal} kcal'den az`);
    if (filters.min_energy_kcal) messages.push(`Enerji en az ${filters.min_energy_kcal} kcal`);
    if (filters.max_sugar) messages.push(`Şeker %${filters.max_sugar}'ten az`);
    if (filters.max_fat) messages.push(`Yağ %${filters.max_fat}'ten az`);
    if (filters.max_saturated_fat) messages.push(`Doymuş yağ %${filters.max_saturated_fat}'ten az`);
    if (filters.max_salt) messages.push(`Tuz %${filters.max_salt}'ten az`);
    if (filters.max_sodium) messages.push(`Sodyum %${filters.max_sodium}'ten az`);
    if (filters.min_fiber) messages.push(`Lif en az %${filters.min_fiber}`);
    if (filters.min_proteins) messages.push(`Protein en az %${filters.min_proteins}`);
    if (filters.max_proteins) messages.push(`Protein en fazla %${filters.max_proteins}`);
    if (filters.exclude_ingredients) messages.push(`${filters.exclude_ingredients} içermeyen`);
    if (filters.include_ingredients) messages.push(`${filters.include_ingredients} içeren`);
    if (filters.is_vegan) messages.push(`Sadece vegan`);
    if (filters.is_vegetarian) messages.push(`Sadece vejetaryen`);
    if (filters.nutriscore_grade) messages.push(`Nutri-Score: ${filters.nutriscore_grade.toUpperCase()}`);
    if (filters.nova_group) messages.push(`NOVA Grubu: ${filters.nova_group}`);
    if (filters.additives) messages.push(`Katkı maddeleri: ${filters.additives}`);

    if (filters.categories.length > 0) {
      const selectedLabels = filters.categories
        .map(cat => categoriesOptions.find(opt => opt.tag === cat)?.label || cat)
        .join(', ');
      messages.push(`Kategoriler: ${selectedLabels}`);
    }

    return messages.length > 0 ? messages.join(', ') + ' ürünler listeleniyor.' : '';
  };

  const categoriesOptions = [
    { tag: "en:beverages", label: "İçecekler" },
    { tag: "en:juices", label: "Meyve Suları" },
    { tag: "en:snacks", label: "Atıştırmalıklar" },
    { tag: "en:dairy-products", label: "Süt Ürünleri" },
    { tag: "en:fruits", label: "Meyveler" },
    { tag: "en:breads", label: "Ekmekler" },
    { tag: "en:cereals", label: "Tahıllar" },
    { tag: "en:sweets", label: "Tatlılar" },
    { tag: "en:vegetables", label: "Sebzeler" },
    { tag: "en:meat-products", label: "Et Ürünleri" },
    { tag: "en:fats-and-oils", label: "Yağlar" },
    { tag: "en:fish-and-seafood", label: "Balık ve Deniz Ürünleri" },
    { tag: "en:sauces", label: "Soslar" },
    { tag: "en:confectionery", label: "Şekerlemeler" },
    { tag: "en:ready-meals", label: "Hazır Yemekler" },
  ];

  return (
    <div style={{ paddingTop: '100px' }}>
      <div className="product-search-container">
        <h1 className="search-title">Ürün Arama</h1>

        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ürün arayın..."
          className="search-input"
        />

        <h2 className="filter-title">Filtreleme Seçenekleri</h2>

        <div className="filters">
          <input
            type="number"
            name="max_energy_kcal"
            value={filters.max_energy_kcal}
            onChange={handleFilterChange}
            placeholder="Maks. enerji (kcal)"
          />
          <input
            type="number"
            name="max_sugar"
            value={filters.max_sugar}
            onChange={handleFilterChange}
            placeholder="Maks. şeker (%)"
          />
          <input
            type="number"
            name="max_fat"
            value={filters.max_fat}
            onChange={handleFilterChange}
            placeholder="Maks. yağ (%)"
          />
          <input
            type="number"
            name="max_saturated_fat"
            value={filters.max_saturated_fat}
            onChange={handleFilterChange}
            placeholder="Maks. doymuş yağ (%)"
          />
          <input
            type="number"
            name="max_salt"
            value={filters.max_salt}
            onChange={handleFilterChange}
            placeholder="Maks. tuz (%)"
          />
          <input
            type="number"
            name="max_sodium"
            value={filters.max_sodium}
            onChange={handleFilterChange}
            placeholder="Maks. sodyum (%)"
          />
          <input
            type="number"
            name="min_fiber"
            value={filters.min_fiber}
            onChange={handleFilterChange}
            placeholder="Min. lif (%)"
          />
          <input
            type="number"
            name="min_proteins"
            value={filters.min_proteins}
            onChange={handleFilterChange}
            placeholder="Min. protein (%)"
          />
          <input
            type="number"
            name="max_proteins"
            value={filters.max_proteins}
            onChange={handleFilterChange}
            placeholder="Maks. protein (%)"
          />
          <input
            type="text"
            name="include_ingredients"
            value={filters.include_ingredients}
            onChange={handleFilterChange}
            placeholder="Zorunlu içerikler"
          />
          <input
            type="text"
            name="exclude_ingredients"
            value={filters.exclude_ingredients}
            onChange={handleFilterChange}
            placeholder="Hariç içerikler"
          />

          <label>
            <input
              type="checkbox"
              name="is_vegan"
              checked={filters.is_vegan}
              onChange={handleFilterChange}
            />
            Vegan
          </label>
          <label>
            <input
              type="checkbox"
              name="is_vegetarian"
              checked={filters.is_vegetarian}
              onChange={handleFilterChange}
            />
            Vejetaryen
          </label>
          <input
            type="text"
            name="nutriscore_grade"
            value={filters.nutriscore_grade}
            onChange={handleFilterChange}
            placeholder="Nutri-Score (örn: A,B)"
          />
          <input
            type="text"
            name="nova_group"
            value={filters.nova_group}
            onChange={handleFilterChange}
            placeholder="NOVA Grup (örn: 1,2)"
          />
          <input
            type="number"
            name="min_energy_kcal"
            value={filters.min_energy_kcal}
            onChange={handleFilterChange}
            placeholder="Min. enerji (kcal)"
          />

          <input
            type="text"
            name="additives"
            value={filters.additives}
            onChange={handleFilterChange}
            placeholder="Katkı maddeleri (virgülle ayrılmış)"
          />

          <div className="category-filters" style={{ display: 'flex', gap: '20px' }}>
            <h3 style={{ width: '100%' }}>Kategoriler</h3>
            {splitIntoChunks(categoriesOptions, 5).map((chunk, index) => (
              <div key={index} style={{ display: 'flex', flexDirection: 'column' }}>
                {chunk.map(({ tag, label }) => (
                  <label key={tag} style={{ marginBottom: '5px' }}>
                    <input
                      type="checkbox"
                      value={tag}
                      checked={filters.categories.includes(tag)}
                      onChange={(e) => {
                        const checked = e.target.checked;
                        setFilters(prev => {
                          const newCategories = checked
                            ? [...prev.categories, tag]
                            : prev.categories.filter(c => c !== tag);
                          return { ...prev, categories: newCategories };
                        });
                      }}
                    />
                    {label}
                  </label>
                ))}
              </div>
            ))}
          </div>
        </div>

        <button
          onClick={handleSearch}
          className="search-button"
          style={{ width: '150px' }}
        >
          Ara
        </button>

        {loading && <p>Yükleniyor...</p>}
        {error && <p className="error">{error}</p>}

        <div className="product-results">
          {getFilterDescription() && (
            <p
              className="filter-description"
              style={{ fontWeight: 'bold', marginBottom: '10px' }}
            >
              {getFilterDescription()}
            </p>
          )}

          {products.map((product) => (
            <div 
              key={product.id || product._id} 
              className="product-item clickable-product"
              onClick={() => handleProductClick(product)}
            >
              <h3>{product.product_name || 'İsim yok'}</h3>
              {product.image_url && (
                <img src={product.image_url} alt={product.product_name} />
              )}
              <p><strong>Marka:</strong> {product.brands}</p>
              <p><strong>Nutri-Score:</strong> {product.nutrition_grade_fr?.toUpperCase() || 'Bilinmiyor'}</p>
              <p><strong>Enerji:</strong> {product.nutriments?.energy_kcal ? `${product.nutriments.energy_kcal} kcal` : 'Veri yok'}</p>
              <p className="click-hint">Detaylar ve uyarılar için tıklayın →</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ProductSearch;