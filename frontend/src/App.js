import React, { useEffect } from 'react';
import logo from './static/Logo.png';
import './App.css';
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import R201_1 from "./templates/201.1.js";
import R201_2 from "./templates/201.2.js";
import R202 from "./templates/202.js";
import R204 from "./templates/204.js";
import R205 from "./templates/205.js";
import R206 from "./templates/206.js";
import R207 from "./templates/207.js";
import R208 from "./templates/208.js";
import R209 from "./templates/209.js";
import R210 from "./templates/210.js";
import R211_1 from "./templates/211.1.js";
import R211_2 from "./templates/211.2.js";
import R212 from "./templates/212.js";
import MHL from "./templates/MHL.js";
import MSL from "./templates/MSL.js";
import Home from "./templates/Home.js";


function App() {
  const bellIds = [
    "201_1", "201_2", "202", "204", "205", "206", "207", "208", "209", "210", "211_1", "211_2", "212", "MHL", "MSL"
  ];

  useEffect (() => {
      window.addEventListener("scroll", function() {
        let header = document.getElementById("header");
        if (window.scrollY > 50) {
            header.classList.add("shrink");
        } else {
            header.classList.remove("shrink");
        }
  });

  

  window.addEventListener("load", function() {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  }, []);




  return (
    <Router className='div'>
      <header id='header'>
        <link rel="preconnect" href="https://fonts.googleapis.com"/>
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
        <link href="https://fonts.googleapis.com/css2?family=Exo+2&display=swap" rel="stylesheet"/>
        <a href='/bell/home'><img src={logo} alt="Логотип школи"/></a>
        <nav>
          <Link to="/bell/home" className='header_but'>Головна</Link>
          {bellIds.map((id) => (
            <Link to={`/bell/room${id}`} className='header_but'>
              {id}
            </Link>
          ))}
        </nav>
      </header>
      <Routes className="routes">
        <Route path="/bell/home" element={<Home />} />
        <Route path="/bell/room201_1" element={<R201_1 />} />
        <Route path="/bell/room201_2" element={<R201_2 />} />
        <Route path="/bell/room202" element={<R202 />} />
        <Route path="/bell/room204" element={<R204 />} />
        <Route path="/bell/room205" element={<R205 />} />
        <Route path="/bell/room206" element={<R206 />} />
        <Route path="/bell/room207" element={<R207 />} />
        <Route path="/bell/room208" element={<R208 />} />
        <Route path="/bell/room209" element={<R209 />} />
        <Route path="/bell/room210" element={<R210 />} />
        <Route path="/bell/room211_1" element={<R211_1 />} />
        <Route path="/bell/room211_2" element={<R211_2 />} />
        <Route path="/bell/room212" element={<R212 />} />
        <Route path="/bell/roomMHL" element={<MHL />} />
        <Route path="/bell/roomMSL" element={<MSL />} />
      </Routes>
      <footer>
        <p>Brobots</p>
        {//<a href="https://school-site.com">Сайт школи</a>
        //<a href="https://instagram.com/school">Instagram</a>
        //<a href="https://tiktok.com/school">TikTok</a>
        //<a href="https://youtube.com/school">YouTube</a>
        }
      </footer>    
      <script src="../static/js/last_melody.js"></script>
    </Router>
  );
}

export default App;
