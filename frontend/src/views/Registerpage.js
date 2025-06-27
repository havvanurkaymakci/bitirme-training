import { useState, useContext } from 'react'
import { Link } from 'react-router-dom'
import AuthContext from '../context/AuthContext'
import '../styles/RegisterPage.css'

function RegisterPage() {
  const [email, setEmail] = useState("")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [password2, setPassword2] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [errors, setErrors] = useState({})
  const { registerUser } = useContext(AuthContext)

  const handleSubmit = async e => {
    e.preventDefault()
    setIsLoading(true)
    setErrors({})

    try {
      // Form validation
      if (password !== password2) {
        setErrors({ password2: "Passwords don't match" })
        setIsLoading(false)
        return
      }

      if (password.length < 8) {
        setErrors({ password: "Password must be at least 8 characters" })
        setIsLoading(false)
        return
      }

      // Email validation
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(email)) {
        setErrors({ email: "Please enter a valid email address" })
        setIsLoading(false)
        return
      }

      // Username validation
      if (username.length < 3) {
        setErrors({ username: "Username must be at least 3 characters" })
        setIsLoading(false)
        return
      }

      // Call registerUser from AuthContext
      const result = await registerUser(email, username, password, password2)
      
      // Handle registration result if needed
      if (result && result.error) {
        setErrors(result.error)
      }
    } catch (error) {
      console.error('Registration error:', error)
      setErrors({ general: 'Registration failed. Please try again.' })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div style={{ paddingTop: '80px' }}>
      <div className="register-page">
        <section className="form-wrapper">
          <div className="form-card">
            <div className="form-content">
              <form onSubmit={handleSubmit}>
                <h2>Welcome to <b>NutriGuide.ai</b></h2>
                <p className="subtitle">Sign Up</p>

                {errors.general && (
                  <div className="error-message general-error">
                    {errors.general}
                  </div>
                )}

                <div className="input-group">
                  <input
                    type="email"
                    placeholder="Email Address"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    disabled={isLoading}
                    required
                  />
                  {errors.email && (
                    <span className="error-message">
                      {Array.isArray(errors.email) ? errors.email[0] : errors.email}
                    </span>
                  )}
                </div>

                <div className="input-group">
                  <input
                    type="text"
                    placeholder="Username"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    disabled={isLoading}
                    required
                  />
                  {errors.username && (
                    <span className="error-message">
                      {Array.isArray(errors.username) ? errors.username[0] : errors.username}
                    </span>
                  )}
                </div>

                <div className="input-group">
                  <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    disabled={isLoading}
                    required
                  />
                  {errors.password && (
                    <span className="error-message">
                      {Array.isArray(errors.password) ? errors.password[0] : errors.password}
                    </span>
                  )}
                </div>

                <div className="input-group">
                  <input
                    type="password"
                    placeholder="Confirm Password"
                    value={password2}
                    onChange={e => setPassword2(e.target.value)}
                    disabled={isLoading}
                    required
                  />
                  {errors.password2 && (
                    <span className="error-message">
                      {Array.isArray(errors.password2) ? errors.password2[0] : errors.password2}
                    </span>
                  )}
                </div>

                {/* Non-field errors (genel hatalar) */}
                {errors.non_field_errors && (
                  <div className="error-message general-error">
                    {Array.isArray(errors.non_field_errors) 
                      ? errors.non_field_errors.join(', ') 
                      : errors.non_field_errors}
                  </div>
                )}

                <button type="submit" disabled={isLoading}>
                  {isLoading ? 'Creating Account...' : 'Register'}
                </button>

                <p className="text">
                  Already have an account? <Link to="/login">Login Now</Link>
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
  )
}

export default RegisterPage