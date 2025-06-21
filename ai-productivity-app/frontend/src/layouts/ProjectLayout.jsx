import React from 'react';
import { Outlet, Link, useParams } from 'react-router-dom';

export default function ProjectLayout() {
  const { projectId } = useParams();
  
  return (
    <>
      <nav className="max-w-6xl mx-auto text-sm text-gray-500 py-2 px-4 sm:px-6 lg:px-8" aria-label="Breadcrumb">
        <Link to="/projects" className="hover:underline hover:text-gray-700">
          Projects
        </Link>
        <span className="mx-1">/</span>
        <Link 
          to={`/projects/${projectId}`} 
          className="hover:underline hover:text-gray-700"
        >
          Overview
        </Link>
      </nav>
      <Outlet />
    </>
  );
}