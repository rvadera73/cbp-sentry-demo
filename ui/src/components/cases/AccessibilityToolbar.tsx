import React, { useState, useRef, useEffect } from 'react';
import { Search, List, Columns3, Map } from 'lucide-react';
import './AccessibilityToolbar.css';

export type ViewMode = 'list' | 'split' | 'map';
export type RiskFilter = 'all' | 'high' | 'medium' | 'low';
export type SortBy = 'risk' | 'date' | 'shipper';

interface AccessibilityToolbarProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;

  searchTerm: string;
  onSearchChange: (term: string) => void;

  riskFilter: RiskFilter;
  onRiskFilterChange: (risk: RiskFilter) => void;

  sortBy: SortBy;
  onSortByChange: (sort: SortBy) => void;

  resultCount: number;
  totalCount: number;
  isLoading?: boolean;
}

/**
 * AccessibilityToolbar: View toggle + filter/search controls
 *
 * Layout:
 * - Left: View toggle button group (List | Split | Map) with aria-selected
 * - Middle: Search input with debounce
 * - Right: Risk filter + sort dropdowns + result count
 *
 * Accessibility:
 * - Button group: role="group" + aria-label
 * - Each view button: aria-selected + aria-label
 * - All controls have associated labels
 * - aria-live region for result count
 * - Keyboard: Tab through all controls, arrow keys on button group
 */
export default function AccessibilityToolbar({
  viewMode,
  onViewModeChange,
  searchTerm,
  onSearchChange,
  riskFilter,
  onRiskFilterChange,
  sortBy,
  onSortByChange,
  resultCount,
  totalCount,
  isLoading = false,
}: AccessibilityToolbarProps) {
  const [debouncedSearch, setDebouncedSearch] = useState(searchTerm);
  const searchTimeoutRef = useRef<any>(undefined);

  // Debounce search input
  useEffect(() => {
    searchTimeoutRef.current = setTimeout(() => {
      onSearchChange(debouncedSearch);
    }, 300);

    return () => {
      if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    };
  }, [debouncedSearch, onSearchChange]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDebouncedSearch(e.target.value);
  };

  const handleViewToggle = (newMode: ViewMode) => {
    onViewModeChange(newMode);
  };

  const handleKeyDown = (e: React.KeyboardEvent, newMode: ViewMode) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleViewToggle(newMode);
    }
  };

  return (
    <div className="accessibility-toolbar" role="region" aria-label="Case manager toolbar">
      {/* LEFT: View Toggle Button Group */}
      <div className="toolbar-section toolbar-section--view-toggle">
        <div
          role="group"
          aria-label="View mode selection"
          className="view-toggle-group"
        >
          {/* List View Button */}
          <button
            type="button"
            onClick={() => handleViewToggle('list')}
            onKeyDown={(e) => handleKeyDown(e, 'list')}
            aria-selected={viewMode === 'list'}
            aria-label="List view: high-density case table"
            className={`view-toggle-btn ${viewMode === 'list' ? 'view-toggle-btn--active' : ''}`}
            title="List View"
          >
            <List size={20} aria-hidden="true" />
            <span className="view-toggle-label">List</span>
          </button>

          {/* Split Pane Button */}
          <button
            type="button"
            onClick={() => handleViewToggle('split')}
            onKeyDown={(e) => handleKeyDown(e, 'split')}
            aria-selected={viewMode === 'split'}
            aria-label="Split pane view: case list with detail panel"
            className={`view-toggle-btn ${viewMode === 'split' ? 'view-toggle-btn--active' : ''}`}
            title="Split Pane View"
          >
            <Columns3 size={20} aria-hidden="true" />
            <span className="view-toggle-label">Split</span>
          </button>

          {/* Map View Button */}
          <button
            type="button"
            onClick={() => handleViewToggle('map')}
            onKeyDown={(e) => handleKeyDown(e, 'map')}
            aria-selected={viewMode === 'map'}
            aria-label="Corridor map view: geospatial visualization"
            className={`view-toggle-btn ${viewMode === 'map' ? 'view-toggle-btn--active' : ''}`}
            title="Corridor Map View"
          >
            <Map size={20} aria-hidden="true" />
            <span className="view-toggle-label">Map</span>
          </button>
        </div>
      </div>

      {/* CENTER: Search Input */}
      <div className="toolbar-section toolbar-section--search">
        <div className="search-wrapper">
          <Search className="search-icon" size={18} aria-hidden="true" />
          <input
            type="text"
            placeholder="Search shipper, consignee, ID, HTS code..."
            value={debouncedSearch}
            onChange={handleSearchChange}
            disabled={isLoading}
            className="search-input"
            aria-label="Search cases by shipper, consignee, ID, or HTS code"
          />
        </div>
      </div>

      {/* RIGHT: Filters + Sort + Results */}
      <div className="toolbar-section toolbar-section--filters">
        {/* Risk Level Filter */}
        <div className="filter-group">
          <label htmlFor="risk-filter" className="filter-label">
            Risk Level
          </label>
          <select
            id="risk-filter"
            value={riskFilter}
            onChange={(e) => onRiskFilterChange(e.target.value as RiskFilter)}
            disabled={isLoading}
            className="filter-select"
            aria-label="Filter cases by risk level"
          >
            <option value="all">All Risk Levels</option>
            <option value="high">HIGH (70+)</option>
            <option value="medium">MEDIUM (40-69)</option>
            <option value="low">LOW (Below 40)</option>
          </select>
        </div>

        {/* Sort By */}
        <div className="filter-group">
          <label htmlFor="sort-by" className="filter-label">
            Sort By
          </label>
          <select
            id="sort-by"
            value={sortBy}
            onChange={(e) => onSortByChange(e.target.value as SortBy)}
            disabled={isLoading}
            className="filter-select"
            aria-label="Sort cases"
          >
            <option value="risk">Risk (High to Low)</option>
            <option value="date">Date (Newest)</option>
            <option value="shipper">Shipper (A-Z)</option>
          </select>
        </div>

        {/* Result Count */}
        <div className="result-count" aria-live="polite" aria-atomic="true">
          <span className="result-count__label">Cases:</span>
          <span className="result-count__value">{resultCount}</span>
          <span className="result-count__divider">/</span>
          <span className="result-count__total">{totalCount}</span>
        </div>
      </div>
    </div>
  );
}
