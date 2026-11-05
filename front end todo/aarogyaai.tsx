import React, { useState, useEffect, useRef } from 'react';
import { 
  Heart, 
  Activity, 
  Moon, 
  Droplets, 
  Footprints, 
  ChevronRight, 
  ChevronLeft,
  AlertTriangle,
  Info,
  ShieldCheck,
  Stethoscope,
  Smartphone,
  CheckCircle2,
  Eye,
  EyeOff,
  Lock,
  Mail,
  ArrowRight
} from 'lucide-react';

// --- Illustrations Components (CSS-based & SVG UI mockups) ---

const Illustration1 = ({ isActive }) => (
  <div className="relative w-full max-w-md aspect-square bg-slate-100 rounded-3xl p-6 shadow-inner flex flex-col gap-4 overflow-hidden border border-slate-200">
    <div className={`transition-all duration-1000 delay-300 ${isActive ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'} flex justify-between items-center bg-white p-4 rounded-2xl shadow-sm border border-slate-100`}>
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center text-rose-500">
          <Heart className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <p className="text-xs text-slate-500 font-medium">Heart Rate</p>
          <p className="text-lg font-bold text-slate-900">72 <span className="text-xs font-normal text-slate-400">bpm</span></p>
        </div>
      </div>
      <div className="h-8 w-16 bg-rose-50 rounded-lg overflow-hidden relative">
        <svg viewBox="0 0 100 40" className="absolute bottom-0 w-full h-full stroke-rose-400 fill-none" strokeWidth="3">
          <path d="M0 20 L20 20 L30 5 L40 35 L50 20 L100 20" />
        </svg>
      </div>
    </div>

    <div className="grid grid-cols-2 gap-4 flex-1">
      <div className={`transition-all duration-1000 delay-400 ${isActive ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'} bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between`}>
        <div className="flex items-center gap-2 text-teal-600">
          <Activity className="w-4 h-4" />
          <span className="text-xs font-medium">Blood Pressure</span>
        </div>
        <p className="text-xl font-bold text-slate-900">118/76</p>
      </div>
      
      <div className={`transition-all duration-1000 delay-500 ${isActive ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'} bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between`}>
        <div className="flex items-center gap-2 text-blue-500">
          <Droplets className="w-4 h-4" />
          <span className="text-xs font-medium">SpO₂</span>
        </div>
        <p className="text-xl font-bold text-slate-900">98<span className="text-sm font-normal text-slate-400">%</span></p>
      </div>

      <div className={`transition-all duration-1000 delay-600 ${isActive ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'} bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between`}>
        <div className="flex items-center gap-2 text-indigo-500">
          <Moon className="w-4 h-4" />
          <span className="text-xs font-medium">Sleep</span>
        </div>
        <p className="text-xl font-bold text-slate-900">7<span className="text-sm font-normal text-slate-400">h</span> 20<span className="text-sm font-normal text-slate-400">m</span></p>
      </div>

      <div className={`transition-all duration-1000 delay-700 ${isActive ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'} bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between`}>
        <div className="flex items-center gap-2 text-orange-500">
          <Footprints className="w-4 h-4" />
          <span className="text-xs font-medium">Activity</span>
        </div>
        <p className="text-xl font-bold text-slate-900">6,432</p>
      </div>
    </div>
  </div>
);

const Illustration2 = ({ isActive }) => (
  <div className="relative w-full max-w-md aspect-square bg-slate-900 rounded-3xl p-6 shadow-xl flex flex-col items-center justify-center overflow-hidden">
    <div className="absolute inset-0 opacity-20">
      <div className="w-full h-full border-b border-slate-700" style={{ background: 'linear-gradient(to right, transparent 1px, transparent 1px, #0f172a 1px, #0f172a 20px), linear-gradient(to bottom, #334155 1px, transparent 1px, transparent 20px)', backgroundSize: '20px 20px' }}></div>
    </div>
    
    <svg viewBox="0 0 400 300" className="w-full h-full absolute inset-0 z-10" preserveAspectRatio="none">
      {/* Baseline */}
      <path d="M 0 150 Q 100 150 200 150 T 400 150" stroke="#334155" strokeWidth="2" strokeDasharray="5,5" fill="none" />
      
      {/* Trend line 1 (Heart Rate) */}
      <path 
        d="M 0 180 Q 100 220 200 120 T 400 90" 
        stroke="#2DD4BF" 
        strokeWidth="4" 
        fill="none" 
        strokeLinecap="round"
        style={{
          strokeDasharray: 600,
          strokeDashoffset: isActive ? 0 : 600,
          transition: 'stroke-dashoffset 2s ease-in-out 0.3s'
        }}
      />
      {/* Trend line 2 (SpO2) */}
      <path 
        d="M 0 100 Q 150 100 200 160 T 400 180" 
        stroke="#818CF8" 
        strokeWidth="3" 
        fill="none" 
        strokeLinecap="round"
        style={{
          strokeDasharray: 600,
          strokeDashoffset: isActive ? 0 : 600,
          transition: 'stroke-dashoffset 2s ease-in-out 0.6s'
        }}
      />
    </svg>

    <div className={`z-20 bg-white/10 backdrop-blur-md border border-white/20 p-4 rounded-xl shadow-lg transition-all duration-700 delay-1000 ${isActive ? 'opacity-100 scale-100' : 'opacity-0 scale-90'}`}>
      <div className="flex items-center gap-2 mb-2">
        <div className="w-2 h-2 rounded-full bg-teal-400"></div>
        <span className="text-white text-xs font-medium">Individual Baseline</span>
      </div>
      <p className="text-slate-300 text-xs">AI correlates multiple vectors to find unique patterns.</p>
    </div>
  </div>
);

const Illustration3 = ({ isActive }) => (
  <div className="relative w-full max-w-md aspect-square bg-slate-50 rounded-3xl p-6 shadow-inner flex flex-col items-center justify-center overflow-hidden border border-slate-200">
    <div className="w-full max-w-sm space-y-4 z-10">
      
      <div className={`bg-white p-5 rounded-2xl shadow-lg border-l-4 border-amber-500 transition-all duration-700 delay-300 ${isActive ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-8'}`}>
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-full bg-amber-50 flex items-center justify-center text-amber-500 shrink-0">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-slate-900 font-bold text-sm">Elevated Risk Detected</h4>
            <p className="text-slate-500 text-xs mt-1">Pattern indicates potential anomaly requiring attention.</p>
          </div>
        </div>
      </div>

      <div className={`bg-white p-4 rounded-2xl shadow-sm border border-slate-100 transition-all duration-700 delay-600 ${isActive ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
        <div className="flex items-center gap-2 text-slate-700 mb-3 border-b border-slate-100 pb-2">
          <Info className="w-4 h-4 text-teal-600" />
          <span className="text-xs font-semibold uppercase tracking-wider">Contributing Factors</span>
        </div>
        <ul className="space-y-3">
          <li className="flex items-center justify-between">
            <span className="text-sm text-slate-600 flex items-center gap-2"><Heart className="w-3 h-3 text-rose-400"/> HR resting avg up</span>
            <span className="text-xs font-bold text-rose-500">+12%</span>
          </li>
          <li className="flex items-center justify-between">
            <span className="text-sm text-slate-600 flex items-center gap-2"><Moon className="w-3 h-3 text-indigo-400"/> Sleep efficiency</span>
            <span className="text-xs font-bold text-amber-500">-15%</span>
          </li>
        </ul>
      </div>

    </div>
  </div>
);

const Illustration4 = ({ isActive }) => (
  <div className="relative w-full max-w-md aspect-square bg-slate-100 rounded-3xl p-6 shadow-inner flex items-center justify-center overflow-hidden border border-slate-200">
    
    {/* Connecting line */}
    <div className="absolute inset-0 flex items-center justify-center z-0">
      <div className="w-48 h-0.5 bg-slate-300 relative border-t-2 border-dashed border-slate-300">
        <div className={`absolute w-3 h-3 bg-teal-500 rounded-full -top-1.5 transition-all duration-2000 ease-in-out ${isActive ? 'left-full opacity-0' : 'left-0 opacity-100'}`} style={{ animation: isActive ? 'slideDot 2s infinite' : 'none' }}></div>
      </div>
    </div>
    
    <style dangerouslySetInnerHTML={{__html: `
      @keyframes slideDot {
        0% { left: 10%; opacity: 0; }
        10% { opacity: 1; }
        90% { opacity: 1; }
        100% { left: 90%; opacity: 0; }
      }
    `}} />

    {/* Mobile Screen (Patient) */}
    <div className={`absolute left-8 z-10 w-32 h-56 bg-white rounded-2xl shadow-xl border-4 border-slate-800 flex flex-col overflow-hidden transition-all duration-700 delay-300 ${isActive ? 'opacity-100 -rotate-3 translate-y-0' : 'opacity-0 rotate-0 translate-y-8'}`}>
      <div className="bg-slate-800 h-4 w-full flex justify-center">
        <div className="w-8 h-1.5 bg-slate-600 rounded-b-lg"></div>
      </div>
      <div className="p-3 flex-1 flex flex-col gap-2">
        <div className="flex items-center gap-1 text-teal-600 mb-2">
          <ShieldCheck className="w-4 h-4" />
          <span className="text-[10px] font-bold">Aarogya</span>
        </div>
        <div className="w-full h-12 bg-slate-50 rounded-lg border border-slate-100 flex items-center p-2 gap-2">
          <Heart className="w-4 h-4 text-rose-400" />
          <div className="w-10 h-1 bg-slate-200 rounded-full"></div>
        </div>
        <div className="w-full h-12 bg-slate-50 rounded-lg border border-slate-100 flex items-center p-2 gap-2">
          <Moon className="w-4 h-4 text-indigo-400" />
          <div className="w-8 h-1 bg-slate-200 rounded-full"></div>
        </div>
      </div>
    </div>

    {/* Desktop Screen (Doctor) */}
    <div className={`absolute right-4 z-20 w-52 h-40 bg-white rounded-xl shadow-2xl border-4 border-slate-800 flex flex-col overflow-hidden transition-all duration-700 delay-500 ${isActive ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
       <div className="bg-slate-100 border-b border-slate-200 h-6 flex items-center px-2 gap-1">
         <div className="w-2 h-2 rounded-full bg-rose-400"></div>
         <div className="w-2 h-2 rounded-full bg-amber-400"></div>
         <div className="w-2 h-2 rounded-full bg-green-400"></div>
       </div>
       <div className="p-3 flex gap-2 h-full">
         <div className="w-12 h-full bg-slate-50 border border-slate-100 rounded flex flex-col items-center py-2 gap-2">
           <div className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center text-slate-500">
             <Stethoscope className="w-3 h-3" />
           </div>
           <div className="w-8 h-1 bg-slate-200 rounded-full"></div>
           <div className="w-8 h-1 bg-slate-200 rounded-full"></div>
         </div>
         <div className="flex-1 flex flex-col gap-2">
           <div className="w-full h-4 bg-teal-50 rounded flex items-center px-1">
             <span className="text-[8px] font-bold text-teal-700">Patient #482 Overview</span>
           </div>
           <div className="w-full flex-1 bg-slate-50 border border-slate-100 rounded relative overflow-hidden">
             <svg viewBox="0 0 100 40" className="absolute bottom-0 w-full h-full stroke-slate-300 fill-none" strokeWidth="1">
                <path d="M0 30 Q 25 10 50 25 T 100 20" />
             </svg>
             <div className="absolute top-2 left-2 bg-amber-100 text-amber-700 text-[6px] px-1 rounded font-bold border border-amber-200">Alert</div>
           </div>
         </div>
       </div>
    </div>
  </div>
);

// --- Content Data ---

const slidesData = [
  {
    id: 0,
    title: "Your Health, Continuously Monitored",
    subtitle: "Track the signals that matter.",
    text: "Aarogya AI continually monitors five key health indicators: Heart Rate, Blood Pressure, SpO₂, Sleep Schedule, and Physical Activity to provide a comprehensive view of your well-being.",
    Illustration: Illustration1
  },
  {
    id: 1,
    title: "Understand Patterns, Not Just Numbers",
    subtitle: "Every patient is different.",
    text: "Instead of relying on fixed thresholds, our system analyses multiple health signals together, establishing individual baselines to understand what is truly normal for you.",
    Illustration: Illustration2
  },
  {
    id: 2,
    title: "Early Insights, Clearer Alerts",
    subtitle: "Know what needs attention.",
    text: "AI-assisted analysis identifies potentially concerning patterns early. We prioritize alerts and provide clear explanations of the specific indicators contributing to a risk assessment.",
    Illustration: Illustration3
  },
  {
    id: 3,
    title: "Connected Care, Informed Decisions",
    subtitle: "Better awareness. More informed care.",
    text: "Empower yourself and your healthcare providers. Share intelligent health insights to support timely follow-ups and comprehensive clinical reviews.",
    disclaimer: "Disclaimer: AI-assisted monitoring, not a medical diagnosis.",
    Illustration: Illustration4
  }
];

// --- Main Components ---

export default function App() {
  const [currentView, setCurrentView] = useState('onboarding'); // 'onboarding' or 'login'

  const navigateToLogin = () => setCurrentView('login');

  return (
    <div className="min-h-screen w-full font-sans text-slate-900 bg-white overflow-hidden selection:bg-teal-100 selection:text-teal-900">
      {currentView === 'onboarding' ? (
        <Onboarding onComplete={navigateToLogin} />
      ) : (
        <LoginScreen onBack={() => setCurrentView('onboarding')} />
      )}
    </div>
  );
}

function Onboarding({ onComplete }) {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const timerRef = useRef(null);
  const pauseTimeoutRef = useRef(null);

  // Auto-transition logic
  useEffect(() => {
    if (isPaused) {
      clearInterval(timerRef.current);
      return;
    }

    timerRef.current = setInterval(() => {
      setCurrentSlide((prev) => {
        if (prev === slidesData.length - 1) {
          // Pause at the last slide instead of looping, user action required to login
          setIsPaused(true);
          return prev;
        }
        return prev + 1;
      });
    }, 5000);

    return () => clearInterval(timerRef.current);
  }, [isPaused]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      clearInterval(timerRef.current);
      clearTimeout(pauseTimeoutRef.current);
    };
  }, []);

  const handleInteraction = (action) => {
    setIsPaused(true);
    action();
    
    // Resume auto-transition after 10 seconds of inactivity
    clearTimeout(pauseTimeoutRef.current);
    pauseTimeoutRef.current = setTimeout(() => {
      if (currentSlide !== slidesData.length - 1) {
        setIsPaused(false);
      }
    }, 10000);
  };

  const nextSlide = () => {
    if (currentSlide < slidesData.length - 1) {
      handleInteraction(() => setCurrentSlide(prev => prev + 1));
    }
  };

  const prevSlide = () => {
    if (currentSlide > 0) {
      handleInteraction(() => setCurrentSlide(prev => prev - 1));
    }
  };

  const goToSlide = (index) => {
    handleInteraction(() => setCurrentSlide(index));
  };

  return (
    <div className="relative w-full h-screen flex flex-col bg-slate-50">
      {/* Top Bar */}
      <div className="absolute top-0 left-0 right-0 p-6 flex justify-between items-center z-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-slate-900 flex items-center justify-center text-teal-400">
            <Activity className="w-5 h-5" />
          </div>
          <span className="font-bold text-slate-900 tracking-tight hidden sm:block">Aarogya AI</span>
        </div>
        <button 
          onClick={onComplete}
          className="text-slate-500 hover:text-slate-900 font-medium text-sm transition-colors px-4 py-2 rounded-full hover:bg-slate-200/50"
        >
          Skip
        </button>
      </div>

      {/* Slider Track */}
      <div 
        className="flex-1 w-full h-full flex transition-transform duration-700 ease-in-out"
        style={{ transform: `translateX(-${currentSlide * 100}%)` }}
      >
        {slidesData.map((slide, index) => (
          <div key={slide.id} className="w-full h-full flex-shrink-0 flex items-center justify-center px-6 pt-20 pb-32 md:pb-24">
            <div className="w-full max-w-5xl mx-auto flex flex-col md:flex-row items-center gap-12 lg:gap-24">
              
              {/* Text Content */}
              <div className="flex-1 flex flex-col gap-6 md:max-w-xl">
                <div className="space-y-2 overflow-hidden">
                  <h3 className={`text-teal-600 font-semibold tracking-wide uppercase text-sm transition-all duration-700 delay-100 ${currentSlide === index ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
                    {slide.subtitle}
                  </h3>
                  <h1 className={`text-4xl md:text-5xl lg:text-6xl font-extrabold text-slate-900 leading-tight transition-all duration-700 delay-200 ${currentSlide === index ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
                    {slide.title}
                  </h1>
                </div>
                <p className={`text-lg text-slate-600 leading-relaxed transition-all duration-700 delay-300 ${currentSlide === index ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
                  {slide.text}
                </p>
                {slide.disclaimer && (
                  <p className={`text-xs text-slate-400 font-medium italic mt-2 transition-all duration-700 delay-400 ${currentSlide === index ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
                    {slide.disclaimer}
                  </p>
                )}
              </div>

              {/* Illustration Container */}
              <div className="flex-1 w-full flex justify-center lg:justify-end">
                <slide.Illustration isActive={currentSlide === index} />
              </div>

            </div>
          </div>
        ))}
      </div>

      {/* Bottom Navigation */}
      <div className="absolute bottom-0 left-0 right-0 p-6 md:p-12 z-50">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          
          {/* Pagination Indicators */}
          <div className="flex items-center gap-3">
            {slidesData.map((_, idx) => (
              <button
                key={idx}
                onClick={() => goToSlide(idx)}
                className={`transition-all duration-300 rounded-full h-2 ${
                  currentSlide === idx 
                    ? 'w-8 bg-teal-500' 
                    : 'w-2 bg-slate-300 hover:bg-slate-400'
                }`}
                aria-label={`Go to slide ${idx + 1}`}
              />
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end">
            <button
              onClick={prevSlide}
              disabled={currentSlide === 0}
              className={`flex items-center justify-center w-12 h-12 rounded-full border border-slate-200 text-slate-600 transition-all ${
                currentSlide === 0 ? 'opacity-0 invisible' : 'opacity-100 hover:bg-white hover:shadow-md'
              }`}
            >
              <ChevronLeft className="w-5 h-5" />
            </button>

            {currentSlide < slidesData.length - 1 ? (
              <button
                onClick={nextSlide}
                className="flex items-center gap-2 bg-slate-900 text-white px-6 py-3 rounded-full font-medium hover:bg-slate-800 transition-all shadow-lg shadow-slate-900/20 active:scale-95"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={onComplete}
                className="flex items-center gap-2 bg-teal-600 text-white px-8 py-3 rounded-full font-medium hover:bg-teal-700 transition-all shadow-lg shadow-teal-600/30 active:scale-95"
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}

function LoginScreen() {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-slate-50 p-6">
      
      {/* Decorative Background Elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-teal-100 rounded-full blur-3xl opacity-50"></div>
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-slate-200 rounded-full blur-3xl opacity-50"></div>
      </div>

      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 p-8 sm:p-10 relative z-10 flex flex-col">
        
        {/* Header */}
        <div className="flex flex-col items-center text-center mb-10">
          <div className="w-12 h-12 rounded-xl bg-slate-900 flex items-center justify-center text-teal-400 mb-6 shadow-md shadow-slate-900/20">
            <Activity className="w-7 h-7" />
          </div>
          <h2 className="text-3xl font-extrabold text-slate-900 mb-2">Welcome to Aarogya AI</h2>
          <p className="text-slate-500 font-medium">Your health insights, thoughtfully connected.</p>
        </div>

        {/* Form */}
        <form className="space-y-5" onSubmit={(e) => e.preventDefault()}>
          <div className="space-y-1.5">
            <label className="text-sm font-semibold text-slate-700 ml-1">Email Address</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Mail className="h-5 w-5 text-slate-400" />
              </div>
              <input 
                type="email" 
                placeholder="name@example.com" 
                className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500 transition-all"
                required
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between items-center ml-1">
              <label className="text-sm font-semibold text-slate-700">Password</label>
              <a href="#" className="text-xs font-semibold text-teal-600 hover:text-teal-700">Forgot Password?</a>
            </div>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Lock className="h-5 w-5 text-slate-400" />
              </div>
              <input 
                type={showPassword ? "text" : "password"} 
                placeholder="••••••••" 
                className="w-full pl-11 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500 transition-all"
                required
              />
              <button 
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
              >
                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
          </div>

          <button 
            type="submit" 
            className="w-full bg-slate-900 text-white font-semibold py-3.5 rounded-xl hover:bg-slate-800 transition-all shadow-lg shadow-slate-900/20 active:scale-[0.98] mt-2"
          >
            Sign In
          </button>
        </form>

        <div className="mt-8 mb-6 relative flex items-center justify-center">
          <div className="absolute w-full h-px bg-slate-200"></div>
          <span className="relative bg-white px-4 text-xs font-medium text-slate-400 uppercase tracking-wider">Or continue with</span>
        </div>

        <button type="button" className="w-full flex items-center justify-center gap-3 bg-white border border-slate-200 text-slate-700 font-semibold py-3.5 rounded-xl hover:bg-slate-50 transition-all active:scale-[0.98]">
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          Google
        </button>

        <p className="text-center text-sm font-medium text-slate-600 mt-8">
          Don't have an account? <a href="#" className="text-teal-600 font-bold hover:text-teal-700">Create Account</a>
        </p>

        <div className="mt-8 pt-6 border-t border-slate-100 flex justify-center">
          <p className="text-[10px] text-slate-400 text-center max-w-xs leading-relaxed">
            Aarogya AI provides AI-assisted monitoring insights and is not a replacement for professional medical diagnosis or treatment.
          </p>
        </div>

      </div>
    </div>
  );
}