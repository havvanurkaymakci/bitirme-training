import { useContext } from 'react';
import { Link } from 'react-router-dom';
import AuthContext from '../context/AuthContext';
import '../styles/Loginpage.css'; // Yeni CSS dosyası

function LoginPage() {
  const { loginUser } = useContext(AuthContext);

  const handleSubmit = (e) => {
    e.preventDefault();
    const email = e.target.email.value;
    const password = e.target.password.value;
    if (email.length > 0) loginUser(email, password);
  };

  return (
    <div style={{ paddingTop: '80px' }}>
      <div className="login-page">
        <section className="form-wrapper">
          <div className="form-card">
            <div className="form-content">
              <form onSubmit={handleSubmit}>
                <h2>Welcome to <b>NutriGuide.ai</b></h2>
                <p className="subtitle">Login</p>

                <input
                  type="email"
                  name="email"
                  placeholder="Email Address"
                  required
                />
                <input
                  type="password"
                  name="password"
                  placeholder="Password"
                  required
                />

                <button type="submit">Login</button>

                <p className="text">
                  Don't have an account? <Link to="/register">Register Now</Link>
                </p>
                <div className="footer-links">
                  <a href="#!">Forgot password?</a>
                  <a href="#!">Terms of use</a>
                  <a href="#!">Privacy policy</a>
                </div>
              </form>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default LoginPage;
