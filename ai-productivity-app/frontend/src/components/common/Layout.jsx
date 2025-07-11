import PropTypes from "prop-types";
import AppShell from "./AppShell";

export default function Layout({ children }) {
  return <AppShell>{children}</AppShell>;
}

Layout.propTypes = {
  children: PropTypes.node.isRequired,
};
