import React, { useContext, useEffect, useState } from 'react';
import AuthContext from '../context/AuthContext';
import { Link, useNavigate } from 'react-router-dom';
import '../styles/UserProfilePage.css';

function UserProfilePage() {
  const { user, authTokens } = useContext(AuthContext);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchUserProfile = async () => {
      try {
        if (!authTokens) {
          navigate('/login');
          return;
        }

        const response = await fetch('http://127.0.0.1:8000/api/profile/', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + String(authTokens.access),
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          console.error('Profile fetch error:', errorData);
          return;
        }

        const data = await response.json();
        console.log('Profile data:', data); // Debug için
        setProfile(data);
      } catch (error) {
        console.error('Error fetching profile:', error);
      } finally {
        setLoading(false);
      }
    };

    if (authTokens) {
      fetchUserProfile();
    }
  }, [authTokens, navigate]);

  // Helper function to format array values
  const formatArrayValue = (value, displayValue = null) => {
    if (displayValue && typeof displayValue === 'string') {
      return displayValue;
    }
    
    if (Array.isArray(value) && value.length > 0) {
      return value.join(', ');
    }
    
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
    
    return "None";
  };

  // Helper function to format activity level
  const formatActivityLevel = (value) => {
    const activityLabels = {
      'sedentary': 'Sedentary (Hareketsiz)',
      'light': 'Light Activity (Hafif Aktivite)',
      'moderate': 'Moderate Activity (Orta Aktivite)',
      'active': 'Active (Aktif)',
      'very_active': 'Very Active (Çok Aktif)'
    };
    
    return activityLabels[value] || value || "Not set";
  };

  // Helper function to format health goals
  const formatHealthGoals = (goals) => {
    if (!Array.isArray(goals) || goals.length === 0) {
      return "None";
    }

    const goalLabels = {
      'weight_loss': 'Kilo Verme',
      'weight_gain': 'Kilo Alma',
      'muscle_building': 'Kas Geliştirme',
      'general_health': 'Genel Sağlık',
      'endurance': 'Dayanıklılık',
      'strength': 'Güç',
      'flexibility': 'Esneklik',
      'stress_management': 'Stres Yönetimi',
      'better_sleep': 'Daha İyi Uyku',
      'disease_prevention': 'Hastalık Önleme'
    };

    return goals.map(goal => goalLabels[goal] || goal).join(', ');
  };

  if (loading) {
    return <div className="text-center mt-5"><h3>Loading...</h3></div>;
  }

  return (
    <div style={{ paddingTop: '80px' }}>
       
    <div className="user-profile-page-wrapper d-flex justify-content-center py-5 px-3 bg-light">
    <div className="user-profile-container w-100 px-4" style={{ maxWidth: '1400px' }}>
      <div className="row g-4">
        <div className="col-lg-4">
          <div className="card h-100 shadow-sm border-0">
            <div className="card-body text-center">
  
            <img 
              src="/img/userprofilepage.jpg" 
              alt="avatar"
              className="rounded-circle img-fluid mb-3"
              style={{ width: '150px', height: '150px', objectFit: 'cover' }} 
            />
                <h5 className="my-3">{user?.username || "User"}</h5>
                <p className="text-muted mb-1">{profile?.full_name || "Full Name"}</p>
                <p className="text-muted mb-4">Healthy Nutrition Guide User</p>
                <div className="d-flex justify-content-center gap-2">
                  <Link to="/edit-profile" className="btn btn-primary">Edit Profile</Link>
                </div>
              </div>
            </div>
          </div>

          <div className="col-lg-8">

          <div className="card shadow-sm border-0 mb-4 w-100">
             <div className="card-body px-4 py-3">
                <p className="mb-4 text-primary fw-semibold">Welcome to your Healthy Nutrition Guide profile</p>
                <p className="mb-2" style={{ fontSize: '0.9rem' }}>Your nutrition journey starts here</p>
                <div className="progress rounded" style={{ height: '6px' }}>
                  <div className="progress-bar bg-success" role="progressbar" style={{ width: '80%' }} aria-valuenow="80" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
              </div>
            </div>

          {/* Basic Information Card */}
          <div className="card shadow-sm border-0 mb-4 w-100">
             <div className="card-body px-4 py-3">
                <h6 className="card-title text-primary mb-3">Basic Information</h6>
                <ProfileRow label="Full Name" value={profile?.full_name || "Not set"} />
                <ProfileRow label="Email" value={user?.email || "Not available"} />
                <ProfileRow label="Username" value={user?.username || "Not available"} />
                <ProfileRow label="Age" value={profile?.age || "Not set"} />
                <ProfileRow label="Gender" value={profile?.gender || "Not set"} />
              </div>
            </div>

          {/* Physical Information Card */}
          <div className="card shadow-sm border-0 mb-4 w-100">
             <div className="card-body px-4 py-3">
                <h6 className="card-title text-primary mb-3">Physical Information</h6>
                <ProfileRow label="Height (cm)" value={profile?.height || "Not set"} />
                <ProfileRow label="Weight (kg)" value={profile?.weight || "Not set"} />
                <ProfileRow label="BMI" value={profile?.bmi ? profile.bmi.toFixed(2) : "Not calculated"} />
                <ProfileRow 
                  label="Activity Level" 
                  value={formatActivityLevel(profile?.activity_level)} 
                />
              </div>
            </div>

          {/* Health Goals Card */}
          <div className="card shadow-sm border-0 mb-4 w-100">
             <div className="card-body px-4 py-3">
                <h6 className="card-title text-primary mb-3">Health Goals</h6>
                <ProfileRow 
                  label="Health Goals" 
                  value={formatHealthGoals(profile?.health_goals)} 
                />
              </div>
            </div>

          {/* Medical Information Card */}
          <div className="card shadow-sm border-0 mb-4 w-100">
             <div className="card-body px-4 py-3">
                <h6 className="card-title text-primary mb-3">Medical Information</h6>
                <ProfileRow 
                  label="Medical Conditions" 
                  value={formatArrayValue(
                    profile?.medical_conditions, 
                    profile?.medical_conditions_display
                  )} 
                />
                <ProfileRow 
                  label="Allergies" 
                  value={formatArrayValue(
                    profile?.allergies, 
                    profile?.allergies_display
                  )} 
                />
                <ProfileRow 
                  label="Dietary Preferences" 
                  value={formatArrayValue(
                    profile?.dietary_preferences, 
                    profile?.dietary_preferences_display
                  )} 
                />
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>

    </div>
  );
}

function ProfileRow({ label, value }) {
  return (
    <div className="profile-info-row">
      <div className="profile-info-label">{label}</div>
      <div className="profile-info-value">{value}</div>
    </div>
  );
}

export default UserProfilePage;