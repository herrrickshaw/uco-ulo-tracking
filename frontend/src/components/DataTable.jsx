export default function DataTable({ columns, rows, emptyMessage = "No data yet." }) {
  if (!rows || rows.length === 0) {
    return <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-400">{emptyMessage}</div>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            {columns.map((col) => (
              <th key={col.key} className="px-4 py-2 text-left font-medium text-slate-500">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row, i) => (
            <tr key={row.id ?? i} className="hover:bg-slate-50">
              {columns.map((col) => (
                <td key={col.key} className="whitespace-nowrap px-4 py-2 text-slate-700">
                  {col.render ? col.render(row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
