import PropTypes from 'prop-types';
import AppShell from './AppShell';
import ThemeDebug from '../ThemeDebug';

export default function Layout({ children }) {
  return (
    <>
      <AppShell>{children}</AppShell>
      {import.meta.env.DEV && <ThemeDebug />}
    </>
  );
}

Layout.propTypes = {
  children: PropTypes.node.isRequired
};
