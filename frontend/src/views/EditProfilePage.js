import React, { useContext, useEffect, useState } from 'react';
import AuthContext from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

function EditProfilePage() {
  const { authTokens } = useContext(AuthContext);
  const navigate = useNavigate();
  const [profile, setProfile] = useState({
    full_name: '',
    age: '',
    gender: '',
    height: '',
    weight: '',
    bmi: '',
    medical_conditions: [],
    allergies: [],
    dietary_preferences: [],
    activity_level: 'moderate', // Backend'deki default değer
    health_goals: [] // Backend'deki alan
  });
  
  // Choices for dropdowns
  const [choices, setChoices] = useState({
    medical_conditions_choices: [],
    allergies_choices: [],
    dietary_preferences_choices: []
  });
  
  // Activity level seçenekleri - Backend models.py'deki choices ile uyumlu
  const activityLevelChoices = [
    ['low', 'Düşük'],
    ['moderate', 'Orta'], 
    ['high', 'Yüksek']
  ];
  
  // Health goals seçenekleri - Bu değerler backend'de validasyon yapılmıyor, 
  // bu yüzden frontend'de tanımlıyoruz
  const healthGoalsOptions = [
    { value: 'weight_loss', label: 'Kilo Verme' },
    { value: 'weight_gain', label: 'Kilo Alma' },
    { value: 'muscle_building', label: 'Kas Geliştirme' },
    { value: 'general_health', label: 'Genel Sağlık' },
    { value: 'endurance', label: 'Dayanıklılık' },
    { value: 'strength', label: 'Güç' },
    { value: 'flexibility', label: 'Esneklik' },
    { value: 'stress_management', label: 'Stres Yönetimi' },
    { value: 'better_sleep', label: 'Daha İyi Uyku' },
    { value: 'disease_prevention', label: 'Hastalık Önleme' }
  ];
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/profile/', {
          headers: {
            'Authorization': 'Bearer ' + String(authTokens.access),
          },
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Fetched data:', data); // Debug için
        
        setProfile({
          full_name: data.full_name || '',
          age: data.age || 18, // Backend default değeri
          gender: data.gender || '',
          height: data.height || '',
          weight: data.weight || '',
          bmi: data.bmi || '',
          medical_conditions: Array.isArray(data.medical_conditions) ? data.medical_conditions : [],
          allergies: Array.isArray(data.allergies) ? data.allergies : [],
          dietary_preferences: Array.isArray(data.dietary_preferences) ? data.dietary_preferences : [],
          activity_level: data.activity_level || 'moderate', // Backend default değeri
          health_goals: Array.isArray(data.health_goals) ? data.health_goals : [] // Backend default değeri
        });
        
        // Set choices for dropdowns
        setChoices({
          medical_conditions_choices: Array.isArray(data.medical_conditions_choices) ? data.medical_conditions_choices : [],
          allergies_choices: Array.isArray(data.allergies_choices) ? data.allergies_choices : [],
          dietary_preferences_choices: Array.isArray(data.dietary_preferences_choices) ? data.dietary_preferences_choices : []
        });
      } catch (err) {
        console.error('Fetch error:', err);
        setError('Failed to load profile: ' + err.message);
      } finally {
        setLoading(false);
      }
    };

    if (authTokens?.access) {
      fetchProfile();
    }
  }, [authTokens]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setProfile(prev => ({ ...prev, [name]: value }));
  };

  const handleMultiSelectChange = (fieldName, value) => {
    setProfile(prev => {
      const currentValues = Array.isArray(prev[fieldName]) ? prev[fieldName] : [];
      let newValues;
      
      if (currentValues.includes(value)) {
        // Remove if already selected
        newValues = currentValues.filter(item => item !== value);
      } else {
        // Add if not selected
        newValues = [...currentValues, value];
      }
      
      console.log(`${fieldName} updated:`, newValues); // Debug için
      return { ...prev, [fieldName]: newValues };
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
  
    const payload = { ...profile };
    delete payload.bmi; // Backend hesaplıyor, frontend'den gönderme
    
    // Numeric alanları doğru formatta gönder
    if (payload.age) payload.age = parseInt(payload.age);
    if (payload.height) payload.height = parseFloat(payload.height);
    if (payload.weight) payload.weight = parseFloat(payload.weight);
    
    console.log('Submitting payload:', payload); // Debug için
  
    try {
      const response = await fetch('http://127.0.0.1:8000/api/profile/update/', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + String(authTokens.access),
        },
        body: JSON.stringify(payload),
      });
  
      if (response.ok) {
        navigate('/profile');
      } else {
        const errorData = await response.json();
        console.error('Update failed:', errorData);
        setError('Profile update failed: ' + JSON.stringify(errorData));
      }
    } catch (err) {
      console.error('Request error:', err);
      setError('An error occurred while updating: ' + err.message);
    }
  };

  const renderMultiSelectField = (fieldName, choices, title) => {
    const currentValues = Array.isArray(profile[fieldName]) ? profile[fieldName] : [];
    const choicesArray = Array.isArray(choices) ? choices : [];
    
    if (choicesArray.length === 0) {
      return (
        <div className="mb-3">
          <label className="form-label">{title}</label>
          <div className="alert alert-info">No options available</div>
        </div>
      );
    }

    return (
      <div className="mb-3">
        <label className="form-label">{title}</label>
        <div className="border rounded p-3" style={{ maxHeight: '200px', overflowY: 'auto' }}>
          {choicesArray.map((choice) => {
            // Backend'den gelen veri formatını kontrol et - tuple formatı [key, display_name]
            let value, label;
            if (Array.isArray(choice) && choice.length >= 2) {
              [value, label] = choice;
            } else if (typeof choice === 'object' && choice.value && choice.label) {
              value = choice.value;
              label = choice.label;
            } else if (typeof choice === 'string') {
              value = choice;
              label = choice;
            } else {
              console.warn('Unknown choice format:', choice);
              return null;
            }

            return (
              <div key={value} className="form-check">
                <input
                  className="form-check-input"
                  type="checkbox"
                  id={`${fieldName}_${value}`}
                  checked={currentValues.includes(value)}
                  onChange={() => handleMultiSelectChange(fieldName, value)}
                />
                <label className="form-check-label" htmlFor={`${fieldName}_${value}`}>
                  {label}
                </label>
              </div>
            );
          })}
        </div>
        {currentValues.length > 0 && (
          <div className="mt-2">
            <small className="text-muted">
              Seçilenler: {currentValues.length} adet
            </small>
            <br />
            <small className="text-muted">
              {currentValues.join(', ')}
            </small>
          </div>
        )}
      </div>
    );
  };

  const renderHealthGoalsField = () => {
    const currentValues = Array.isArray(profile.health_goals) ? profile.health_goals : [];
    
    return (
      <div className="mb-3">
        <label className="form-label">Health Goals (Sağlık Hedefleri)</label>
        <div className="border rounded p-3" style={{ maxHeight: '200px', overflowY: 'auto' }}>
          {healthGoalsOptions.map((goal) => {
            return (
              <div key={goal.value} className="form-check">
                <input
                  className="form-check-input"
                  type="checkbox"
                  id={`health_goals_${goal.value}`}
                  checked={currentValues.includes(goal.value)}
                  onChange={() => handleMultiSelectChange('health_goals', goal.value)}
                />
                <label className="form-check-label" htmlFor={`health_goals_${goal.value}`}>
                  {goal.label}
                </label>
              </div>
            );
          })}
        </div>
        {currentValues.length > 0 && (
          <div className="mt-2">
            <small className="text-muted">
              Seçilenler: {currentValues.length} adet
            </small>
            <br />
            <small className="text-muted">
              {currentValues.map(value => {
                const goal = healthGoalsOptions.find(g => g.value === value);
                return goal ? goal.label : value;
              }).join(', ')}
            </small>
          </div>
        )}
      </div>
    );
  };

  if (loading) return <div className="container" style={{ paddingTop: '80px' }}><p>Loading...</p></div>;

  return (
    <div style={{ paddingTop: '80px' }}>
      <div className="container py-4">
        <h3>Edit Profile</h3>
        {error && <div className="alert alert-danger">{error}</div>}

        <div className="row">
          <div className="col-md-4 d-flex justify-content-center">
            <img
              src="/img/editprofilepage.jpg"
              alt="Profile"
              className="img-fluid rounded-circle mb-4"
              style={{ width: '200px', height: '200px', objectFit: 'cover' }}
            />
          </div>
          
          <div className="col-md-8">
            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="form-label">Full Name</label>
                <input
                  type="text"
                  name="full_name"
                  className="form-control"
                  value={profile.full_name}
                  onChange={handleChange}
                  required
                />
              </div>
              
              <div className="mb-3">
                <label className="form-label">Age</label>
                <input
                  type="number"
                  name="age"
                  className="form-control"
                  value={profile.age}
                  onChange={handleChange}
                  min="1"
                  max="120"
                  required
                />
              </div>
              
              <div className="mb-3">
                <label className="form-label">Gender</label>
                <select
                  name="gender"
                  className="form-control"
                  value={profile.gender}
                  onChange={handleChange}
                >
                  <option value="">Select Gender</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              
              <div className="mb-3">
                <label className="form-label">Height (cm)</label>
                <input
                  type="number"
                  step="0.1"
                  name="height"
                  className="form-control"
                  value={profile.height}
                  onChange={handleChange}
                  min="50"
                  max="300"
                />
              </div>
              
              <div className="mb-3">
                <label className="form-label">Weight (kg)</label>
                <input
                  type="number"
                  step="0.1"
                  name="weight"
                  className="form-control"
                  value={profile.weight}
                  onChange={handleChange}
                  min="20"
                  max="500"
                />
              </div>

              {/* Activity Level Select - Backend choices ile uyumlu */}
              <div className="mb-3">
                <label className="form-label">Activity Level (Aktivite Seviyesi)</label>
                <select
                  name="activity_level"
                  className="form-control"
                  value={profile.activity_level}
                  onChange={handleChange}
                >
                  {activityLevelChoices.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Health Goals Multi-Select */}
              {renderHealthGoalsField()}

              {/* Medical Conditions Multi-Select */}
              {renderMultiSelectField('medical_conditions', choices.medical_conditions_choices, 'Medical Conditions (Tıbbi Durumlar)')}

              {/* Allergies Multi-Select */}
              {renderMultiSelectField('allergies', choices.allergies_choices, 'Allergies (Alerjiler)')}

              {/* Dietary Preferences Multi-Select */}
              {renderMultiSelectField('dietary_preferences', choices.dietary_preferences_choices, 'Dietary Preferences (Beslenme Tercihleri)')}

              <div className="mb-3">
                <label className="form-label">BMI (Automatically Calculated)</label>
                <input 
                  type="text" 
                  className="form-control" 
                  value={profile.bmi ? profile.bmi.toFixed(2) : ''} 
                  readOnly 
                  style={{ backgroundColor: '#f8f9fa' }}
                />
                <small className="form-text text-muted">
                  BMI is automatically calculated based on your height and weight.
                </small>
              </div>

              <div className="d-flex gap-2">
                <button className="btn btn-success" type="submit">
                  Save Changes
                </button>
                <button 
                  className="btn btn-secondary" 
                  type="button" 
                  onClick={() => navigate('/profile')}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default EditProfilePage;