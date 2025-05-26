import { useContext } from 'react'
import { jwtDecode } from "jwt-decode";
import AuthContext from '../context/AuthContext'
import { Link } from 'react-router-dom'
import '../styles/Navbar.css'

function Navbar() {
  const { logoutUser } = useContext(AuthContext)
  const token = localStorage.getItem("authTokens")

  let user_id = null
  if (token) {
    const decoded = jwtDecode(JSON.parse(token).access)
    user_id = decoded.user_id
  }

  return (
    <nav className="navbar navbar-expand-lg navbar-custom fixed-top">
      <div className="container-fluid">
        <Link className="navbar-brand" to="/">
          <img src="/img/logo.png" alt="Logo" style={{ width: "80px", height: "auto" }} />
        </Link>

        <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
          <span className="navbar-toggler-icon"></span>
        </button>

        <div className="collapse navbar-collapse" id="navbarNav">
          <ul className="navbar-nav">
            <li className="nav-item">
              <Link className="nav-link active" to="/">Home</Link>
            </li>

            <li className="nav-item">
              <Link className="nav-link" to="/product-search">Product Search</Link>
            </li>

            {!token && (
              <>
                <li className="nav-item">
                  <Link className="nav-link" to="/login">Login</Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/register">Register</Link>
                </li>
              </>
            )}

            {token && (
              <>
                <li className="nav-item">
                  <Link className="nav-link" to="/profile">Profile</Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/edit-profile">Edit Profile</Link>
                </li>
                <li className="nav-item">
                  <a className="nav-link" onClick={logoutUser} style={{ cursor: "pointer" }}>Logout</a>
                </li>
              </>
            )}
          </ul>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
