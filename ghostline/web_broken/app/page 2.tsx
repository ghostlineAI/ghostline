import Link from 'next/link';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col">
      {/* Hero Section */}
      <section className="relative flex flex-col items-center justify-center min-h-[90vh] px-6 text-center bg-gradient-to-b from-slate-50 to-slate-100">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-slate-900 mb-6">
            Your AI-Powered
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-pink-600"> Ghost-Writing </span>
            Platform
          </h1>
          <p className="text-xl md:text-2xl text-slate-600 mb-8 max-w-3xl mx-auto">
            Transform your ideas into professionally written books with our multi-agent AI system. 
            Capture your unique voice and style in every page.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link 
              href="/auth/register" 
              className="px-8 py-4 bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors text-lg font-medium text-center"
            >
              Start Writing Free
            </Link>
            <Link 
              href="/auth/login" 
              className="px-8 py-4 bg-white text-slate-900 rounded-lg hover:bg-slate-50 transition-colors text-lg font-medium border border-slate-200 text-center"
            >
              Sign In
            </Link>
          </div>
        </div>
        <div className="absolute bottom-10 animate-bounce">
          <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-4 text-slate-900">
            Write Better, Faster, Together
          </h2>
          <p className="text-xl text-center text-slate-600 mb-16 max-w-3xl mx-auto">
            Our AI agents work alongside you to research, outline, write, and refine your book
          </p>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <h3 className="text-2xl font-semibold mb-2 text-slate-900">AI-Powered Research</h3>
              <p className="text-slate-600">Our agents analyze your source materials and extract key themes, maintaining your voice throughout</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-pink-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-pink-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </div>
              <h3 className="text-2xl font-semibold mb-2 text-slate-900">Collaborative Writing</h3>
              <p className="text-slate-600">Work with specialized AI agents that handle research, writing, editing, and consistency checks</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-indigo-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-2xl font-semibold mb-2 text-slate-900">Voice Matching</h3>
              <p className="text-slate-600">Advanced AI ensures every page sounds like you, with ≥0.88 voice similarity score</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-6 bg-slate-900 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-bold mb-4">Ready to Write Your Book?</h2>
          <p className="text-xl mb-8 text-slate-300">Join thousands of authors using AI to bring their stories to life</p>
          <Link 
            href="/auth/register" 
            className="inline-block px-8 py-4 bg-white text-slate-900 rounded-lg hover:bg-slate-100 transition-colors text-lg font-medium"
          >
            Get Started Free
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 bg-white border-t border-slate-200">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center">
          <p className="text-slate-600 mb-4 md:mb-0">© 2025 GhostLine AI. All rights reserved.</p>
          <nav className="flex gap-6">
            <a href="#" className="text-slate-600 hover:text-slate-900 transition-colors">Privacy</a>
            <a href="#" className="text-slate-600 hover:text-slate-900 transition-colors">Terms</a>
            <a href="#" className="text-slate-600 hover:text-slate-900 transition-colors">Contact</a>
          </nav>
        </div>
      </footer>
    </main>
  );
}
