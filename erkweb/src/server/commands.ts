import {readFile, readdir} from 'fs/promises';
import {basename, join} from 'path';

export interface CommandInfo {
  name: string;
  description: string;
  argumentHint: string;
}

async function safeReaddir(dir: string): Promise<string[]> {
  try {
    return await readdir(dir);
  } catch {
    return [];
  }
}

async function extractDescription(filePath: string): Promise<string> {
  try {
    const content = await readFile(filePath, 'utf-8');
    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) {
        continue;
      }
      // Skip markdown headings and frontmatter
      if (trimmed.startsWith('#') || trimmed === '---') {
        continue;
      }
      // Return first content line, truncated
      return trimmed.length > 80 ? trimmed.slice(0, 80) + '...' : trimmed;
    }
  } catch {
    // ignore read errors
  }
  return '';
}

export async function discoverCommands(cwd: string): Promise<CommandInfo[]> {
  const commands: CommandInfo[] = [];
  const claudeDir = join(cwd, '.claude');

  // Scan .claude/commands/ for .md files and namespace subdirectories
  const commandsDir = join(claudeDir, 'commands');
  const commandEntries = await safeReaddir(commandsDir);

  for (const entry of commandEntries) {
    const entryPath = join(commandsDir, entry);
    if (entry.endsWith('.md')) {
      const name = basename(entry, '.md');
      const description = await extractDescription(entryPath);
      commands.push({name, description, argumentHint: ''});
    } else if (!entry.includes('.')) {
      // Namespace directory — scan for .md files inside
      const nsEntries = await safeReaddir(entryPath);
      for (const nsEntry of nsEntries) {
        if (nsEntry.endsWith('.md')) {
          const cmdName = basename(nsEntry, '.md');
          const description = await extractDescription(join(entryPath, nsEntry));
          commands.push({name: `${entry}:${cmdName}`, description, argumentHint: ''});
        }
      }
    }
  }

  // Scan .claude/skills/ for skill directories
  const skillsDir = join(claudeDir, 'skills');
  const skillEntries = await safeReaddir(skillsDir);

  for (const entry of skillEntries) {
    if (entry.includes('.')) {
      continue;
    }
    // Try to read the skill's main file for a description
    const skillFile = join(skillsDir, entry, `${entry}.md`);
    const description = await extractDescription(skillFile);
    commands.push({name: entry, description, argumentHint: ''});
  }

  commands.sort((a, b) => a.name.localeCompare(b.name));
  return commands;
}
