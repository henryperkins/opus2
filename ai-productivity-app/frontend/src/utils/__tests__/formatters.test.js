import { describe, it, expect } from "vitest";
import { formatDate, formatFileSize, formatTimeAgo } from "../formatters";

describe("Formatters", () => {
  describe("formatDate", () => {
    it("formats dates correctly", () => {
      const date = new Date("2024-01-15T10:30:00Z");
      const result = formatDate(date);
      expect(result).toMatch(/Jan 15, 2024/);
    });

    it("handles string dates", () => {
      const result = formatDate("2024-01-15T10:30:00Z");
      expect(result).toMatch(/Jan 15, 2024/);
    });

    it("handles invalid dates", () => {
      const result = formatDate("invalid-date");
      expect(result).toBe("Invalid Date");
    });
  });

  describe("formatFileSize", () => {
    it("formats bytes correctly", () => {
      expect(formatFileSize(0)).toBe("0 B");
      expect(formatFileSize(512)).toBe("512 B");
      expect(formatFileSize(1024)).toBe("1.0 KB");
      expect(formatFileSize(1536)).toBe("1.5 KB");
      expect(formatFileSize(1048576)).toBe("1.0 MB");
      expect(formatFileSize(1073741824)).toBe("1.0 GB");
    });

    it("handles negative values", () => {
      expect(formatFileSize(-100)).toBe("0 B");
    });
  });

  describe("formatTimeAgo", () => {
    it("formats time differences correctly", () => {
      const now = new Date();
      const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
      const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);

      expect(formatTimeAgo(fiveMinutesAgo)).toBe("5 minutes ago");
      expect(formatTimeAgo(oneHourAgo)).toBe("1 hour ago");
      expect(formatTimeAgo(oneDayAgo)).toBe("1 day ago");
    });

    it("handles future dates", () => {
      const future = new Date(Date.now() + 60000);
      expect(formatTimeAgo(future)).toBe("just now");
    });
  });
});
