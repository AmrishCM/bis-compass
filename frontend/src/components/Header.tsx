import { Link } from 'react-router-dom';

export const Header = () => {
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="max-w-6xl mx-auto py-4 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
        <div className="flex space-x-3 items-center">
          <Link to="/" className="text-xl font-bold text-gray-800">
            BIS Compass
          </Link>
          <p className="text-sm text-gray-500">Bureau of Indian Standards Certification Assistant</p>
        </div>
        <nav className="flex space-x-4">
          <Link to="/" className="px-4 py-3 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
            Home
          </Link>
          <Link to="/analysis" className="px-4 py-3 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
            Analysis
          </Link>
          <Link to="/history" className="px-4 py-3 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
            History
          </Link>
        </nav>
      </div>
    </header>
  );
};