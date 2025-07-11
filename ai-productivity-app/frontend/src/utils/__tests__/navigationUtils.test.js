import { describe, it, expect } from "vitest";
import {
  isActivePath,
  generateBreadcrumbs,
  getNavigationItems,
} from "../navigationUtils";

describe("navigationUtils", () => {
  describe("isActivePath", () => {
    it("should match exact root path", () => {
      expect(isActivePath("/", "/")).toBe(true);
      expect(isActivePath("/projects", "/")).toBe(false);
    });

    it("should match path prefixes", () => {
      expect(isActivePath("/projects/123", "/projects")).toBe(true);
      expect(isActivePath("/search/results", "/search")).toBe(true);
      expect(isActivePath("/projects", "/projects")).toBe(true);
    });

    it("should handle case sensitivity", () => {
      expect(isActivePath("/PROJECTS", "/projects")).toBe(true);
      expect(isActivePath("/Projects/123", "/projects")).toBe(true);
    });

    it("should handle URL encoding", () => {
      expect(isActivePath("/projects/%20123", "/projects/ 123")).toBe(true);
      expect(
        isActivePath("/projects/hello%20world", "/projects/hello world"),
      ).toBe(true);
    });

    it("should handle trailing slashes", () => {
      expect(isActivePath("/projects/", "/projects")).toBe(true);
      expect(isActivePath("/projects", "/projects/")).toBe(true);
      expect(isActivePath("/projects/", "/projects/")).toBe(true);
    });

    it("should handle malformed URIs gracefully", () => {
      expect(isActivePath("/projects/%", "/projects")).toBe(true);
      expect(isActivePath("/projects/%ZZ", "/projects")).toBe(true);
    });

    it("should not match unrelated paths", () => {
      expect(isActivePath("/searching", "/search")).toBe(false);
      expect(isActivePath("/timeline", "/time")).toBe(false);
    });

    it("should prevent startsWith false-positives", () => {
      // These should NOT match due to segment boundary logic
      expect(isActivePath("/searching", "/search")).toBe(false);
      expect(isActivePath("/search-broken", "/search")).toBe(false);
      expect(isActivePath("/projectsabc", "/projects")).toBe(false);
      expect(isActivePath("/settingsx", "/settings")).toBe(false);
    });

    it("should match exact path segments", () => {
      // These SHOULD match as they respect segment boundaries
      expect(isActivePath("/search", "/search")).toBe(true);
      expect(isActivePath("/search/results", "/search")).toBe(true);
      expect(isActivePath("/projects/123", "/projects")).toBe(true);
      expect(isActivePath("/projects/123/chat", "/projects")).toBe(true);
      expect(isActivePath("/projects/123/chat/456", "/projects/123")).toBe(
        true,
      );
    });

    it("should handle path segments with query strings", () => {
      expect(isActivePath("/search?q=test", "/search")).toBe(true);
      expect(isActivePath("/projects/123?tab=chat", "/projects")).toBe(true);
      expect(isActivePath("/searching?q=test", "/search")).toBe(false);
    });

    it("should handle path segments with hashes", () => {
      expect(isActivePath("/search#section", "/search")).toBe(true);
      expect(isActivePath("/projects/123#overview", "/projects")).toBe(true);
      expect(isActivePath("/searching#section", "/search")).toBe(false);
    });
  });

  describe("generateBreadcrumbs", () => {
    it("should generate root breadcrumb", () => {
      const breadcrumbs = generateBreadcrumbs("/");
      expect(breadcrumbs).toEqual([{ name: "Dashboard", path: "/" }]);
    });

    it("should generate project breadcrumbs", () => {
      const breadcrumbs = generateBreadcrumbs("/projects");
      expect(breadcrumbs).toEqual([
        { name: "Dashboard", path: "/" },
        { name: "Projects", path: "/projects" },
      ]);
    });

    it("should generate specific project breadcrumbs", () => {
      const breadcrumbs = generateBreadcrumbs("/projects/123");
      expect(breadcrumbs).toEqual([
        { name: "Dashboard", path: "/" },
        { name: "Projects", path: "/projects" },
        { name: "Project", path: "/projects/123" },
      ]);
    });

    it("should generate project sub-page breadcrumbs", () => {
      const breadcrumbs = generateBreadcrumbs("/projects/123/chat");
      expect(breadcrumbs).toEqual([
        { name: "Dashboard", path: "/" },
        { name: "Projects", path: "/projects" },
        { name: "Project", path: "/projects/123" },
        { name: "Chat", path: "/projects/123/chat" },
      ]);
    });

    it("should generate breadcrumbs for known pages", () => {
      const breadcrumbs = generateBreadcrumbs("/search");
      expect(breadcrumbs).toEqual([
        { name: "Dashboard", path: "/" },
        { name: "Search", path: "/search" },
      ]);
    });

    it("should handle unknown pages", () => {
      const breadcrumbs = generateBreadcrumbs("/unknown");
      expect(breadcrumbs).toEqual([
        { name: "Dashboard", path: "/" },
        { name: "Unknown", path: "/unknown" },
      ]);
    });

    it("should handle query strings by stripping them from labels but preserving in final path", () => {
      const breadcrumbs = generateBreadcrumbs("/search?q=test");
      expect(breadcrumbs).toEqual([
        { name: "Dashboard", path: "/" },
        { name: "Search", path: "/search" }, // Clean path, not '/search?q=test'
      ]);
    });

    it("should handle hash fragments by stripping them", () => {
      const breadcrumbs = generateBreadcrumbs("/search#section");
      expect(breadcrumbs).toEqual([
        { name: "Dashboard", path: "/" },
        { name: "Search", path: "/search" },
      ]);
    });

    it("should handle complex query and hash combinations", () => {
      const breadcrumbs = generateBreadcrumbs(
        "/projects/123/chat?tab=messages#recent",
      );
      expect(breadcrumbs).toEqual([
        { name: "Dashboard", path: "/" },
        { name: "Projects", path: "/projects" },
        { name: "Project", path: "/projects/123" },
        { name: "Chat", path: "/projects/123/chat" },
      ]);
    });

    it("should handle trailing slashes", () => {
      const breadcrumbs = generateBreadcrumbs("/projects/");
      expect(breadcrumbs).toEqual([
        { name: "Dashboard", path: "/" },
        { name: "Projects", path: "/projects" }, // Clean path without trailing slash
      ]);
    });

    it("should handle deep nested project routes", () => {
      const breadcrumbs = generateBreadcrumbs(
        "/projects/123/files/images/screenshot.png",
      );
      expect(breadcrumbs).toEqual([
        { name: "Dashboard", path: "/" },
        { name: "Projects", path: "/projects" },
        { name: "Project", path: "/projects/123" },
        { name: "Files", path: "/projects/123/files" },
        { name: "Images", path: "/projects/123/files/images" },
        {
          name: "Screenshot.png",
          path: "/projects/123/files/images/screenshot.png",
        },
      ]);
    });
  });

  describe("getNavigationItems", () => {
    it("should return all items without filters", () => {
      const items = getNavigationItems();
      expect(items.length).toBeGreaterThan(0);
      expect(items.some((item) => item.id === "dashboard")).toBe(true);
    });

    it("should filter by showInSidebar", () => {
      const items = getNavigationItems({ showInSidebar: true });
      expect(items.every((item) => item.showInSidebar === true)).toBe(true);
    });

    it("should filter by showMobileQuickAction", () => {
      const items = getNavigationItems({ showMobileQuickAction: true });
      expect(items.every((item) => item.showMobileQuickAction === true)).toBe(
        true,
      );
    });

    it("should handle multiple filters (AND logic)", () => {
      const items = getNavigationItems({
        showInSidebar: true,
        showMobileQuickAction: true,
      });
      expect(
        items.every(
          (item) =>
            item.showInSidebar === true && item.showMobileQuickAction === true,
        ),
      ).toBe(true);
    });

    it("should return empty array when no items match filters", () => {
      const items = getNavigationItems({
        showMobileQuickAction: false, // Should return empty since all items either have this true or undefined
      });
      expect(items.length).toBe(3); // Only non-mobile-quick-action items (dashboard, projects, timeline)
    });
  });
});
