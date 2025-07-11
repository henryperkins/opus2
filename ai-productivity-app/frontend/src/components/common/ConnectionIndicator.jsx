import PropTypes from "prop-types";

/**
 * Connection indicator pill that shows the current websocket connection
 * state (e.g. connected, connecting, disconnected).
 *
 * Instead of sprinkling conditional Tailwind classes inline, we rely on a
 * single `connection-indicator` class whose appearance is driven purely by
 * a `data-state` attribute. This keeps the markup small and allows all
 * styling logic to live in CSS (globals.css).
 */
export default function ConnectionIndicator({ state, className = "" }) {
  return (
    <span
      className={`connection-indicator ${className}`.trim()}
      data-state={state}
      aria-label={`Connection ${state}`}
    >
      {state === "connecting"
        ? "Connecting…"
        : state === "connected"
          ? "Online"
          : "Offline"}
    </span>
  );
}

ConnectionIndicator.propTypes = {
  state: PropTypes.oneOf(["connected", "connecting", "disconnected", "error"])
    .isRequired,
  className: PropTypes.string,
};
