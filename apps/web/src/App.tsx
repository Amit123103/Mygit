import React, { useState } from 'react';
import {
  GitBranch,
  GitCommit,
  GitPullRequest,
  AlertCircle,
  Folder,
  FileText,
  ShieldCheck,
  Star,
  GitFork,
  Download,
  Terminal,
  CheckCircle2,
  Lock,
  Cpu
} from 'lucide-react';

interface FileItem {
  name: string;
  type: 'dir' | 'file';
  size?: string;
  lastCommit: string;
  time: string;
}

const mockFiles: FileItem[] = [
  { name: 'packages', type: 'dir', lastCommit: 'Implement 3-way merge engine', time: '10 mins ago' },
  { name: 'apps', type: 'dir', lastCommit: 'Add FastAPI remote server endpoints', time: '1 hour ago' },
  { name: 'tests', type: 'dir', lastCommit: 'Add pytest suite for objects & index', time: '2 hours ago' },
  { name: 'README.md', type: 'file', size: '2.4 KB', lastCommit: 'Initial documentation commit', time: '1 day ago' },
  { name: 'pyproject.toml', type: 'file', size: '1.1 KB', lastCommit: 'Add monorepo configuration', time: '1 day ago' },
  { name: '.mygitignore', type: 'file', size: '240 B', lastCommit: 'Ignore build artifacts & venv', time: '1 day ago' },
];

const mockCommits = [
  { sha: 'c83d91f', message: 'Implement 3-way merge engine & LCA graph search', author: 'Developer <developer@example.com>', time: '10 mins ago', verified: true },
  { sha: '81f21a0', message: 'Add content-addressed object store with zlib compression', author: 'Developer <developer@example.com>', time: '1 hour ago', verified: true },
  { sha: '5f91ac3', message: 'Initial commit: repository structure & CLI framework', author: 'Developer <developer@example.com>', time: '1 day ago', verified: false },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<'code' | 'commits' | 'prs' | 'issues' | 'security'>('code');
  const [selectedBranch, setSelectedBranch] = useState('main');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-gradient-to-r from-blue-500 to-indigo-600 p-2 rounded-lg text-white shadow-lg shadow-blue-500/20">
            <Cpu className="w-5 h-5" />
          </div>
          <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            MyGit
          </span>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
            v1.0.0
          </span>
        </div>

        <div className="flex items-center space-x-4 text-sm">
          <div className="bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/50 text-slate-300 flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-slate-400" />
            <span className="font-mono text-xs text-blue-400">mygit clone http://localhost:8000/repo</span>
          </div>

          <button className="bg-blue-600 hover:bg-blue-500 text-white font-medium px-4 py-1.5 rounded-lg transition-all shadow-md shadow-blue-600/20 flex items-center space-x-2">
            <Download className="w-4 h-4" />
            <span>Clone</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        {/* Repo Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center space-x-2 text-slate-400 text-sm mb-1">
              <span className="text-blue-400 font-medium">developer</span>
              <span>/</span>
              <span className="text-slate-100 font-semibold text-xl">mygit-ecosystem</span>
              <span className="text-xs px-2 py-0.5 rounded-full border border-slate-700 bg-slate-800 text-slate-300">
                Public
              </span>
            </div>
            <p className="text-slate-400 text-sm">
              Independent, content-addressed version control platform built from scratch.
            </p>
          </div>

          <div className="flex items-center space-x-3 text-sm">
            <button className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-2 transition">
              <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
              <span>Star</span>
              <span className="bg-slate-900 px-1.5 py-0.5 rounded text-xs text-slate-400">128</span>
            </button>

            <button className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-2 transition">
              <GitFork className="w-4 h-4 text-slate-400" />
              <span>Fork</span>
              <span className="bg-slate-900 px-1.5 py-0.5 rounded text-xs text-slate-400">14</span>
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 mt-6 space-x-8 text-sm">
          {[
            { id: 'code', label: 'Code', icon: FileText, count: null },
            { id: 'commits', label: 'Commits', icon: GitCommit, count: 3 },
            { id: 'prs', label: 'Pull Requests', icon: GitPullRequest, count: 1 },
            { id: 'issues', label: 'Issues', icon: AlertCircle, count: 2 },
            { id: 'security', label: 'Security & FSCK', icon: ShieldCheck, count: null },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`pb-3 flex items-center space-x-2 font-medium transition border-b-2 ${
                  isActive
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
                {tab.count !== null && (
                  <span className="bg-slate-800 px-2 py-0.5 rounded-full text-xs text-slate-300">
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className="mt-6">
          {activeTab === 'code' && (
            <div>
              {/* Branch Selector Bar */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <button className="bg-slate-900 border border-slate-700 text-slate-200 px-3 py-1.5 rounded-lg flex items-center space-x-2 text-sm font-medium hover:bg-slate-800 transition">
                      <GitBranch className="w-4 h-4 text-blue-400" />
                      <span>{selectedBranch}</span>
                    </button>
                  </div>
                  <span className="text-slate-400 text-sm">
                    <strong className="text-slate-200">2</strong> branches · <strong className="text-slate-200">1</strong> tag
                  </span>
                </div>

                <div className="text-xs text-slate-400 font-mono">
                  Latest Commit SHA: <span className="text-blue-400">c83d91f82e...</span>
                </div>
              </div>

              {/* Files Table */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-xl backdrop-blur">
                <div className="bg-slate-900/80 px-4 py-3 border-b border-slate-800 flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-green-400" />
                    <span className="font-medium text-slate-300">Developer</span>
                    <span>Implement 3-way merge engine & LCA graph search</span>
                  </div>
                  <span>10 mins ago</span>
                </div>

                <div className="divide-y divide-slate-800/60 text-sm">
                  {mockFiles.map((file) => (
                    <div
                      key={file.name}
                      className="px-4 py-3 flex items-center justify-between hover:bg-slate-800/40 transition cursor-pointer"
                    >
                      <div className="flex items-center space-x-3 w-1/3">
                        {file.type === 'dir' ? (
                          <Folder className="w-4 h-4 text-blue-400 fill-blue-500/20" />
                        ) : (
                          <FileText className="w-4 h-4 text-slate-400" />
                        )}
                        <span className="font-medium text-slate-200 hover:text-blue-400 transition">
                          {file.name}
                        </span>
                      </div>
                      <div className="text-slate-400 text-xs w-1/2 truncate">{file.lastCommit}</div>
                      <div className="text-slate-400 text-xs text-right w-1/6">{file.time}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'commits' && (
            <div className="space-y-4">
              <h3 className="font-semibold text-lg text-slate-200">Commit History</h3>
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden divide-y divide-slate-800">
                {mockCommits.map((c) => (
                  <div key={c.sha} className="p-4 flex items-center justify-between hover:bg-slate-800/30 transition">
                    <div>
                      <div className="font-medium text-slate-100 mb-1">{c.message}</div>
                      <div className="text-xs text-slate-400 flex items-center space-x-2">
                        <span>{c.author}</span>
                        <span>·</span>
                        <span>{c.time}</span>
                        {c.verified && (
                          <span className="text-green-400 border border-green-500/30 bg-green-500/10 px-1.5 py-0.5 rounded text-[10px] flex items-center space-x-1">
                            <Lock className="w-3 h-3" />
                            <span>Ed25519 Verified</span>
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="font-mono text-xs text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded border border-blue-500/20">
                      {c.sha}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-6">
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-slate-200 flex items-center space-x-2">
                  <ShieldCheck className="w-5 h-5 text-green-400" />
                  <span>Repository FSCK Integrity Check</span>
                </h3>
                <div className="mt-4 bg-slate-950 border border-slate-800 p-4 rounded-lg font-mono text-sm text-green-400 space-y-1">
                  <div>✓ 1,294 objects checked</div>
                  <div>✓ All hashes valid (SHA-256)</div>
                  <div>✓ Commit graph & 3-way tree references valid</div>
                  <div>✓ No repository corruption detected</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
