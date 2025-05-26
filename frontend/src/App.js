import { Route, Routes } from 'react-router-dom';
import HomePage from './views/Homepage';
import LoginPage from './views/Loginpage';
import Navbar from './views/Navbar';
import RegisterPage from './views/Registerpage';
import Dashboard from './views/Dashboard';
import UserProfilePage from './views/UserProfilePage';
import EditProfilePage from './views/EditProfilePage';
import ProductSearch from './views/ProductSearch';
import ProductDetail from './views/ProductDetail';
import PrivateRoute from './utils/PrivateRoute';
import { AuthProvider } from './context/AuthContext';
import './index.css';

function App() {
  return (
    <AuthProvider>
      <Navbar />
      <div className="main-content">
        <Routes>
          {/* Giriş gerektiren rotalar */}
          <Route element={<PrivateRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/profile" element={<UserProfilePage />} />
            <Route path="/edit-profile" element={<EditProfilePage />} />
          </Route>

          {/* Giriş gerektirmeyen rotalar */}
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/product-search" element={<ProductSearch />} />
          <Route path="/product-detail" element={<ProductDetail />} />
        </Routes>
      </div>
    </AuthProvider>
  );
}
export default App;
