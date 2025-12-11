# Claude AI Assistant Instructions

## Project Overview

This is the Dagster Compass documentation site built with Next.js and Nextra.

## Tech Stack

- **Framework**: Next.js 15.5.3
- **Documentation**: Nextra 2.13.4 (docs theme)
- **React**: 18.3.1
- **TypeScript**: 5.9.2

## Project Structure

```
docs/
├── pages/           # MDX documentation pages
│   ├── index.mdx
│   ├── getting-started.mdx
│   ├── data-exploration.mdx
│   ├── data-management.mdx
│   └── admins/     # Admin section
├── public/images/   # Static assets
├── styles/         # Global CSS with custom dark theme
└── theme.config.tsx # Nextra theme configuration
```

## Key Commands

- `npm run dev` - Start development server on port 3000
- `npm run build` - Build for production
- `npm run start` - Start production server

## Testing Checklist

When making changes, please:

1. **Check for build errors**:

   ```bash
   npm run build
   ```

2. **Verify dark/light mode**:
   - Logos switch correctly
   - Background color is #010e1f in dark mode
   - All text is readable in both modes

3. **Check responsive design**:
   - YouTube embeds are responsive
   - Images max-width is 75%
   - Navigation works on mobile

4. **Validate MDX files**:
   - No syntax errors
   - All links work
   - Embedded videos display correctly

5. **CSS consistency**:
   - Blockquotes have #1c2534 background in dark mode
   - Borders are consistent (10% opacity)
   - No conflicting styles

## Custom Styling Notes

- Dark mode background: `#010e1f`
- Blockquote dark background: `#1c2534`
- Navigation text: 1rem (16px)
- Logo switching uses `useTheme()` hook from `next-themes`

## Common Issues to Check

- TypeScript: `moduleResolution` should be "bundler" not "node"
- Fast Refresh warnings on MDX changes are normal
- Nextra suggests converting \_app.tsx to \_app.mdx (optional)

## Files to Review

- `/styles/globals.css` - All custom styles
- `/theme.config.tsx` - Theme and navigation setup
- `/pages/**/*.mdx` - Content files
- `/public/images/` - Logo and image assets

## Testing Priority

1. Production build succeeds
2. No console errors in browser
3. Dark/light mode works correctly
4. All pages load without errors
5. Navigation works properly

## Contact

For questions about the codebase or deployment, contact the Dagster Compass team.
