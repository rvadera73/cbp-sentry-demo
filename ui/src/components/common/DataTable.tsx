interface Column {
  key: string;
  label: string;
  render?: (value: any, row: any) => React.ReactNode;
  width?: string;
}

interface DataTableProps {
  columns: Column[];
  data: any[];
  striped?: boolean;
  className?: string;
  compact?: boolean;
}

export default function DataTable({
  columns,
  data,
  striped = true,
  className = '',
  compact = false
}: DataTableProps) {
  if (data.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        No data available
      </div>
    );
  }

  const paddingClass = compact ? 'px-2 py-1 text-xs' : 'px-3 py-2 text-sm';

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-gray-100 border-b border-gray-300">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`${paddingClass} text-left font-semibold text-gray-700`}
                style={{ width: col.width }}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr
              key={idx}
              className={`border-b border-gray-200 ${
                striped && idx % 2 === 1 ? 'bg-gray-50' : ''
              }`}
            >
              {columns.map((col) => (
                <td key={col.key} className={paddingClass}>
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
