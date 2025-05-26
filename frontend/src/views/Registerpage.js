import { useState, useContext } from 'react'
import { Link } from 'react-router-dom'
import AuthContext from '../context/AuthContext'
import '../styles/RegisterPage.css' // CSS dosyasını ekledik

function RegisterPage() {
  const [email, setEmail] = useState("")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [password2, setPassword2] = useState("")
  const { registerUser } = useContext(AuthContext)

  const handleSubmit = async e => {
    e.preventDefault()
    registerUser(email, username, password, password2)
  }

  return (
    <div style={{ paddingTop: '80px' }}>
    <div className="register-page">
      <section className="form-wrapper">
        <div className="form-card">
        
          <div className="form-content">
            <form onSubmit={handleSubmit}>
              <h2>Welcome to <b>NutriGuide.ai </b></h2>
              <p className="subtitle">Sign Up</p>

              <input
                type="email"
                placeholder="Email Address"
                onChange={e => setEmail(e.target.value)}
                required
              />
              <input
                type="text"
                placeholder="Username"
                onChange={e => setUsername(e.target.value)}
                required
              />
              <input
                type="password"
                placeholder="Password"
                onChange={e => setPassword(e.target.value)}
                required
              />
              <input
                type="password"
                placeholder="Confirm Password"
                onChange={e => setPassword2(e.target.value)}
                required
              />

              <button type="submit">Register</button>

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
