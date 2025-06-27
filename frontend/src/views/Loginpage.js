import { useState, useContext } from 'react';
import { Link } from 'react-router-dom';
import AuthContext from '../context/AuthContext';
import '../styles/Loginpage.css';

function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const { loginUser } = useContext(AuthContext);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setErrors({});

    try {
      // Form validation
      if (!email || email.length === 0) {
        setErrors({ email: 'Email is required' });
        setIsLoading(false);
        return;
      }

      if (!password || password.length === 0) {
        setErrors({ password: 'Password is required' });
        setIsLoading(false);
        return;
      }

      // Call loginUser from AuthContext
      const result = await loginUser(email, password);
      
      // Handle login result if needed
      if (result && result.error) {
        setErrors(result.error);
      }
    } catch (error) {
      console.error('Login error:', error);
      setErrors({ general: 'Login failed. Please check your credentials.' });
    } finally {
      setIsLoading(false);
    }
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

                {errors.general && (
                  <div className="error-message general-error">
                    {errors.general}
                  </div>
                )}

                {errors.detail && (
                  <div className="error-message general-error">
                    {errors.detail}
                  </div>
                )}

                <div className="input-group">
                  <input
                    type="email"
                    placeholder="Email Address"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={isLoading}
                    required
                  />
                  {errors.email && (
                    <span className="error-message">{errors.email}</span>
                  )}
                </div>

                <div className="input-group">
                  <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={isLoading}
                    required
                  />
                  {errors.password && (
                    <span className="error-message">{errors.password}</span>
                  )}
                </div>

                <button type="submit" disabled={isLoading}>
                  {isLoading ? 'Signing In...' : 'Login'}
                </button>

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