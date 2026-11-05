import { useEffect, useState } from "react";
import logo from "../../assets/images/brand/xbike-logo.svg";

export function LoginCarousel({ slides, interval }) {
  const [{ active, leaving }, setSlide] = useState({ active: 0, leaving: null });
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [hidden, setHidden] = useState(() => document.hidden);
  const [reducedMotion, setReducedMotion] = useState(
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const paused = hovered || focused || hidden || reducedMotion;

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updateMotion = () => setReducedMotion(media.matches);
    const updateVisibility = () => setHidden(document.hidden);
    media.addEventListener("change", updateMotion);
    document.addEventListener("visibilitychange", updateVisibility);
    return () => {
      media.removeEventListener("change", updateMotion);
      document.removeEventListener("visibilitychange", updateVisibility);
    };
  }, []);

  useEffect(() => {
    if (paused || slides.length < 2) return;
    const timer = window.setTimeout(() => {
      setSlide({ active: (active + 1) % slides.length, leaving: active });
    }, interval);
    return () => window.clearTimeout(timer);
  }, [active, paused, interval, slides.length]);

  function goTo(next) {
    if (next !== active) setSlide({ active: next, leaving: active });
  }

  return (
    <section
      className="login-visual"
      aria-roledescription="carousel"
      aria-label="Hình ảnh giới thiệu XBIKE"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false);
      }}
    >
      <div className="login-visual-slides">
        {slides.map((slide, index) => (
          <img
            key={slide.id}
            src={slide.src}
            alt={slide.alt}
            aria-hidden={index !== active}
            className={index === active ? "is-active" : index === leaving ? "is-leaving" : ""}
            loading="eager"
            fetchpriority={index === 0 ? "high" : undefined}
          />
        ))}
      </div>
      <img className="login-logo" src={logo} alt="XBIKE MRP System" />
      <div className="login-visual-content">
        <h2 className="login-tagline">
          Kiểm soát kho.
          <br />
          Điều phối sản xuất.
        </h2>
        <div className="login-thumbs">
          {slides.map((slide, index) => (
            <button
              key={slide.id}
              type="button"
              aria-label={`Xem ảnh ${index + 1}: ${slide.alt}`}
              aria-current={index === active ? "true" : undefined}
              onClick={() => goTo(index)}
            >
              <img src={slide.src} alt="" />
            </button>
          ))}
        </div>
        <div className="login-dots">
          {slides.map((slide, index) => (
            <button
              key={slide.id}
              type="button"
              aria-label={`Ảnh ${index + 1}`}
              aria-current={index === active ? "true" : undefined}
              onClick={() => goTo(index)}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
