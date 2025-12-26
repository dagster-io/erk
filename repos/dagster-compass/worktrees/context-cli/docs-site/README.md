# Dagster Compass Documentation

Documentation site for Dagster Compass - your AI-powered data assistant that works directly in Slack.

## 🚀 Getting Started

This site is built with [Next.js](https://nextjs.org) and [Nextra](https://nextra.site/).

### Prerequisites

- Node.js 18+
- npm

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the site locally.

### Build

```bash
npm run build
npm start
```

## 📁 Project Structure

```
docs/
├── pages/           # Documentation pages
│   ├── index.mdx    # Homepage
│   ├── getting-started.mdx
│   ├── data-exploration.mdx
│   ├── data-management.mdx
│   └── admins/      # Admin documentation
├── public/images/   # Images and assets
├── styles/          # Global CSS
└── theme.config.tsx # Nextra theme configuration
```

## ✏️ Contributing

1. Edit `.mdx` files in the `pages/` directory
2. Add images to `public/images/`
3. Test locally with `npm run dev`
4. Create a pull request

## 📝 Writing Documentation

- Use `.mdx` files for pages (Markdown + JSX)
- Update `pages/_meta.json` for navigation
- Embed videos with standard `<iframe>` tags
- Reference images from `/images/` path

## 🛠️ Built With

- [Next.js](https://nextjs.org) - React framework
- [Nextra](https://nextra.site/) - Documentation framework
- [TypeScript](https://www.typescriptlang.org/) - Type safety
