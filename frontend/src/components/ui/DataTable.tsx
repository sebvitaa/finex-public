import type { ReactNode } from "react";

import { EmptyState } from "./EmptyState";

export type DataTableColumn<T> = {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  align?: "left" | "right";
};

type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  rows: T[];
  getRowKey: (row: T) => string | number;
};

export function DataTable<T>({ columns, rows, getRowKey }: DataTableProps<T>) {
  if (rows.length === 0) {
    return <EmptyState body="Cuando existan movimientos, apareceran aca para revisarlos rapido." title="Sin transacciones" />;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-separate border-spacing-0 text-sm">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                className={`border-b border-border px-3 py-3 text-xs font-medium uppercase text-subtle ${
                  column.align === "right" ? "text-right" : "text-left"
                }`}
                key={column.key}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr className="group" key={getRowKey(row)}>
              {columns.map((column) => (
                <td
                  className={`border-b border-border/70 px-3 py-3 align-middle text-muted group-hover:bg-surface2 ${
                    column.align === "right" ? "text-right" : "text-left"
                  }`}
                  key={column.key}
                >
                  {column.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
