import React from 'react';
import { TYPOGRAPHY, DESIGN } from '../styles/typography';

export interface DataTableColumn {
  key: string;
  label: string;
  width?: string;
  render?: (value: any, row: any) => React.ReactNode;
}

interface DataTableProps {
  title: string;
  columns: DataTableColumn[];
  rows: any[];
  emptyMessage?: string;
  onRowClick?: (row: any) => void;
  loading?: boolean;
}

export default function DataTable({
  title,
  columns,
  rows,
  emptyMessage = 'No data available',
  onRowClick,
  loading = false,
}: DataTableProps) {
  return (
    <div className={`${DESIGN.bgWhite} border ${DESIGN.borderColor} rounded-sm shadow-sm overflow-hidden`}>
      {/* Header */}
      <div className={`bg-[#F0F4F8] border-b ${DESIGN.borderColor} p-4`}>
        <h3 className={`${TYPOGRAPHY.sectionTitle} mb-0`}>{title}</h3>
      </div>

      {/* Table */}
      {loading ? (
        <div className={`p-8 text-center ${DESIGN.textGray} text-xs`}>Loading...</div>
      ) : rows.length === 0 ? (
        <div className={`p-8 text-center ${DESIGN.textGray} text-xs italic`}>{emptyMessage}</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className={`bg-[#F7F9FC] border-b ${DESIGN.borderColor}`}>
                {columns.map((col) => (
                  <th key={col.key} className={`${TYPOGRAPHY.tableHeader} p-3 ${col.width || ''}`}>
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E0E3E8]">
              {rows.map((row, idx) => (
                <tr
                  key={idx}
                  className={`${onRowClick ? 'hover:bg-[#F7F9FC] cursor-pointer' : ''} transition-colors`}
                  onClick={() => onRowClick?.(row)}
                >
                  {columns.map((col) => (
                    <td key={col.key} className={`${TYPOGRAPHY.tableCell} p-3`}>
                      {col.render ? col.render(row[col.key], row) : row[col.key]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
