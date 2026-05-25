import React from 'react';
import { groupComponentsByFactor, formatScore } from './utils';
import { RiskComponentTableProps } from './types';
import './RiskComponentTable.css';

const FACTOR_ORDER = ['Documentation', 'Commodity', 'Routing', 'Party', 'Corridor', 'Pattern', 'Time'];

const RiskComponentTable: React.FC<RiskComponentTableProps> = ({ components }) => {
  if (!components || components.length === 0) {
    return (
      <div className="risk-component-table">
        <p className="no-data">No components to display</p>
      </div>
    );
  }

  const grouped = groupComponentsByFactor(components);
  const sortedFactors = FACTOR_ORDER.filter((f) => f in grouped);

  return (
    <div className="risk-component-table">
      <h3 className="table-title">7-Factor Risk Breakdown</h3>

      {sortedFactors.map((factor) => (
        <div key={factor} className="factor-section">
          <h4 className="factor-name">
            <span className="factor-icon">📊</span>
            {factor} Risk
          </h4>

          <table className="component-details-table">
            <thead>
              <tr>
                <th className="col-component">Component</th>
                <th className="col-score" align="right">
                  Score
                </th>
                <th className="col-weight" align="right">
                  Weight %
                </th>
                <th className="col-calculation" align="right">
                  Calculation
                </th>
                <th className="col-result" align="right">
                  Weighted Result
                </th>
              </tr>
            </thead>
            <tbody>
              {grouped[factor].map((comp, idx) => (
                <tr key={idx} className="component-row">
                  <td className="col-component">
                    <div className="component-info">
                      <div className="component-name">{comp.component}</div>
                      <div className="component-rationale">{comp.rationale}</div>
                      <div className="component-evidence">
                        {comp.evidence.map((e, i) => (
                          <span key={i} className="evidence-item">
                            {e}
                          </span>
                        ))}
                      </div>
                    </div>
                  </td>
                  <td className="col-score" align="right">
                    <span className="score-value">{formatScore(comp.score)}/10</span>
                  </td>
                  <td className="col-weight" align="right">
                    <span className="weight-value">{formatScore(comp.weight)}</span>
                  </td>
                  <td className="col-calculation" align="right">
                    <span className="calculation-value">
                      {formatScore(comp.score)} × {formatScore(comp.weight / 100)}
                    </span>
                  </td>
                  <td className="col-result" align="right">
                    <span className="result-value">{formatScore(comp.weighted_result)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
};

export default RiskComponentTable;
