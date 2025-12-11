interface PaginationProps {
  page: number
  limit: number
  total?: number
  onPageChange: (page: number) => void
  onLimitChange: (limit: number) => void
}

export function Pagination({ page, limit, total, onPageChange, onLimitChange }: PaginationProps) {
  const hasMore = total ? page * limit < total : true

  return (
    <div className="flex items-center justify-between mt-4">
      <div className="flex items-center space-x-2">
        <label className="text-sm text-gray-700">Items per page:</label>
        <select
          value={limit}
          onChange={(e) => onLimitChange(Number(e.target.value))}
          className="form-input py-1 text-sm"
        >
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
          <option value={200}>200</option>
        </select>
      </div>

      <div className="flex items-center space-x-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
          className="btn btn-secondary disabled:opacity-50"
        >
          Previous
        </button>
        <span className="text-sm text-gray-700">
          Page {page}
          {total && ` of ${Math.ceil(total / limit)}`}
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={!hasMore}
          className="btn btn-secondary disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  )
}
