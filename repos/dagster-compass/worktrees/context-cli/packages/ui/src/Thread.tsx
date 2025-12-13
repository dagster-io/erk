import {useEffect, useState} from 'react';
import {useParams} from 'react-router-dom';
import DOMPurify from 'dompurify';

interface ThreadData {
  success: boolean;
  thread_content: string;
  error?: string;
}

export default function Thread() {
  const {team_id, channel_id, thread_ts} = useParams();
  const [data, setData] = useState<ThreadData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchThread = async () => {
      try {
        const response = await fetch(`/api/thread/${team_id}/${channel_id}/${thread_ts}`);
        const result = await response.json();

        if (result.success) {
          setData(result);
        } else {
          setError(result.error || 'Failed to load thread');
        }
      } catch {
        setError('Failed to load thread');
      } finally {
        setLoading(false);
      }
    };

    fetchThread();
  }, [team_id, channel_id, thread_ts]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin h-10 w-10 border-4 border-blue-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-red-600">{error || 'Thread not found'}</div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[900px] mx-auto">
      <style>{`
        .mt-16.w-full.max-w-4xl.flex.flex-col.items-center {
          margin-top: 1rem !important;
        }
      `}</style>

      <div className="px-0 sm:px-6 pb-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-center justify-between mb-8 gap-4">
          <img src="/static/compass-logo.svg" alt="Compass" className="h-10 w-auto" />
          <a
            href="https://docs.compass.dagster.io/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-[15px] font-medium text-blue-600 hover:text-blue-800 transition-colors"
          >
            <i className="ph-bold ph-info"></i>
            Learn more about Compass
          </a>
        </div>

        {/* Thread Content */}
        <div
          className="prose max-w-none"
          dangerouslySetInnerHTML={{__html: DOMPurify.sanitize(data.thread_content)}}
        />

        {/* Footer */}
        <div className="mt-10 pt-8 border-t border-gray-100 text-center">
          <a
            href="https://compass.dagster.io"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <span className="text-md leading-none mb-1">Powered by</span>
            <img src="/static/compass-logo.svg" alt="Compass" className="h-6 w-auto" />
          </a>
        </div>
      </div>
    </div>
  );
}
