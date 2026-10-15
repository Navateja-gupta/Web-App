import { Component, type ErrorInfo, type ReactNode } from "react";

/** Shows a friendly message instead of a blank page if a screen crashes. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled UI error", error, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <h1 className="font-display text-2xl text-maroon-800">Something went wrong</h1>
        <p className="mt-2 text-stone-600">Please reload the page. If the problem continues, contact us.</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-6 rounded-lg bg-maroon-700 px-5 py-2 text-white hover:bg-maroon-800"
        >
          Reload
        </button>
      </div>
    );
  }
}
