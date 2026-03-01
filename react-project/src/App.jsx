import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [stars, setStars] = useState([])

  useEffect(() => {
    const generateStars = () => {
      const newStars = []
      for (let i = 0; i < 200; i++) {
        newStars.push({
          id: i,
          left: Math.random() * 100,
          top: Math.random() * 100,
          size: Math.random() * 3 + 1,
          animationDuration: Math.random() * 3 + 2,
          animationDelay: Math.random() * 2
        })
      }
      setStars(newStars)
    }
    
    generateStars()
  }, [])

  return (
    <div className="night-sky">
      <div className="gradient-overlay"></div>
      {stars.map(star => (
        <div
          key={star.id}
          className="star"
          style={{
            left: `${star.left}%`,
            top: `${star.top}%`,
            width: `${star.size}px`,
            height: `${star.size}px`,
            animationDuration: `${star.animationDuration}s`,
            animationDelay: `${star.animationDelay}s`
          }}
        />
      ))}
      <div className="shooting-star"></div>
      <div className="shooting-star" style={{ animationDelay: '3s', left: '70%' }}></div>
      <div className="constellation">
        <div className="constellation-star"></div>
        <div className="constellation-star" style={{ left: '20px', top: '30px' }}></div>
        <div className="constellation-star" style={{ left: '40px', top: '10px' }}></div>
        <div className="constellation-star" style={{ left: '60px', top: '25px' }}></div>
      </div>
    </div>
  )
}

export default App
