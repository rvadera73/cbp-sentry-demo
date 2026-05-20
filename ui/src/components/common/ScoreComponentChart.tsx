import { ScoreComponent } from '../../types/models';
import DataTable from './DataTable';

interface ScoreComponentChartProps {
  components: ScoreComponent[];
  title?: string;
}

export default function ScoreComponentChart({
  components,
  title = 'Score Breakdown'
}: ScoreComponentChartProps) {
  const columns = [
    {
      key: 'name',
      label: 'Component',
      width: '35%'
    },
    {
      key: 'score',
      label: 'Score',
      width: '15%',
      render: (value: number, row: ScoreComponent) => `${value}/${row.max_score}`
    },
    {
      key: 'percentage',
      label: 'Percentage',
      width: '15%',
      render: (value: number) => `${Math.round(value)}%`
    },
    {
      key: 'factors',
      label: 'Key Factors',
      width: '35%',
      render: (value: string[]) => (
        <ul className="list-disc list-inside text-xs space-y-1">
          {value && value.length > 0 ? (
            value.slice(0, 3).map((factor, idx) => (
              <li key={idx} className="text-gray-700">{factor}</li>
            ))
          ) : (
            <li className="text-gray-500">No factors</li>
          )}
        </ul>
      )
    }
  ];

  return (
    <div>
      {title && <h3 className="font-semibold text-gray-900 mb-3">{title}</h3>}
      <DataTable columns={columns} data={components} compact />
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-900">
          <strong>Total:</strong> {components.reduce((sum, c) => sum + c.score, 0)} / {components.reduce((sum, c) => sum + (c.max_score || c.max || 0), 0)} points
        </p>
      </div>
    </div>
  );
}
