/* Pagination.jsx – generic page navigation component
 *
 * Props
 * -----
 * page        – current (1-based) page number
 * pageCount   – total number of pages (>=1)
 * onPageChange(newPage)
 *
 * Renders «Prev  1 … 4 5 6 … N  Next» with minimal Tailwind styling.
 */

import PropTypes from "prop-types";

const Pagination = ({ page, pageCount, onPageChange }) => {
  if (pageCount <= 1) return null; // nothing to paginate

  const go = (p) => {
    if (p >= 1 && p <= pageCount && p !== page) onPageChange(p);
  };

  // Build a window of page numbers around current page
  const window = 2; // pages left/right of current
  const pages = [];
  for (
    let i = Math.max(1, page - window);
    i <= Math.min(pageCount, page + window);
    i += 1
  ) {
    pages.push(i);
  }

  const showFirstEllipsis = pages[0] > 2;
  const showLastEllipsis = pages[pages.length - 1] < pageCount - 1;

  return (
    <nav
      className="flex items-center justify-center space-x-1 select-none"
      aria-label="Pagination"
    >
      <button
        type="button"
        onClick={() => go(page - 1)}
        disabled={page === 1}
        className="px-2 py-1 text-sm rounded-md border hover:bg-gray-100 disabled:opacity-40"
      >
        Prev
      </button>

      {/* First page */}
      <button
        type="button"
        onClick={() => go(1)}
        className={`px-2 py-1 text-sm rounded-md border ${page === 1 ? "bg-gray-200 font-semibold" : "hover:bg-gray-100"}`}
      >
        1
      </button>

      {showFirstEllipsis && <span className="px-1">…</span>}

      {pages.map(
        (p) =>
          p !== 1 &&
          p !== pageCount && (
            <button
              key={p}
              type="button"
              onClick={() => go(p)}
              className={`px-2 py-1 text-sm rounded-md border ${p === page ? "bg-gray-200 font-semibold" : "hover:bg-gray-100"}`}
            >
              {p}
            </button>
          ),
      )}

      {showLastEllipsis && <span className="px-1">…</span>}

      {pageCount !== 1 && (
        <button
          type="button"
          onClick={() => go(pageCount)}
          className={`px-2 py-1 text-sm rounded-md border ${page === pageCount ? "bg-gray-200 font-semibold" : "hover:bg-gray-100"}`}
        >
          {pageCount}
        </button>
      )}

      <button
        type="button"
        onClick={() => go(page + 1)}
        disabled={page === pageCount}
        className="px-2 py-1 text-sm rounded-md border hover:bg-gray-100 disabled:opacity-40"
      >
        Next
      </button>
    </nav>
  );
};

Pagination.propTypes = {
  page: PropTypes.number.isRequired,
  pageCount: PropTypes.number.isRequired,
  onPageChange: PropTypes.func.isRequired,
};

export default Pagination;
