import React from 'react';
import '../styles/Homepage.css';

function Homepage() {
  return (
    <div className="homepage">
      <div className="hero-section">
        <div className="hero-text">
          <h1>Akıllı Gıda Rehberi</h1>
          <p>Sağlığınıza uygun ürünleri keşfedin. Bilinçli tüketim için buradayız.</p>
        </div>
        <img
          className="hero-image"
          src="https://cdn.eduadvisor.my/posts/2018/06/CourseGuide-Nutrition-Feature-Image.png"
          alt="Healthy food"
        />
      </div>

      <div className="features">
        <h2>Ne Sunuyoruz?</h2>
        <p className="features-info">
          Sağlığınıza uygun ürünleri kolayca bulabilir ve kişisel ihtiyaçlarınıza göre öneriler alabilirsiniz. Alerjen ve katkı maddelerini göz önünde bulundurarak bilinçli tüketim yapın.
        </p>
        <div className="feature-cards">
          <div className="card">
            <img src="https://w7.pngwing.com/pngs/851/233/png-transparent-computer-icons-search-box-button-search-button-text-internet-interface.png" alt="Arama" />
            <p>Ürün arama</p>
          </div>
          <div className="card">
            <img src="https://thumbs.dreamstime.com/b/recommendation-icon-vector-isolated-white-background-sign-transparent-134063044.jpg" alt="Öneriler" />
            <p>Kişiye özel öneriler</p>
          </div>
          <div className="card">
            <img src="https://png.pngtree.com/png-clipart/20230812/original/pngtree-alert-ringer-reminder-art-vector-picture-image_10502088.png" alt="Sağlık" />
            <p>Alerjen ve katkı uyarıları</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Homepage;
