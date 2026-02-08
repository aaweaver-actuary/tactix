import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const SRC_ROOT = path.resolve(__dirname, '..');
const COMPONENTS_DIR = path.join(SRC_ROOT, '_components');
const FLOWS_DIR = path.join(SRC_ROOT, 'flows');

const readText = (filePath: string) => fs.readFileSync(filePath, 'utf8');

const listFiles = (dir: string): string[] =>
  fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const entryPath = path.join(dir, entry.name);
    return entry.isDirectory() ? listFiles(entryPath) : [entryPath];
  });

const isSourceFile = (filePath: string) =>
  ['.ts', '.tsx'].includes(path.extname(filePath));

const isTestFile = (filePath: string) =>
  filePath.includes('.test.') || filePath.includes('.spec.');

const baseComponentNames = () =>
  listFiles(COMPONENTS_DIR)
    .filter((file) => path.extname(file) === '.tsx')
    .filter((file) => !isTestFile(file))
    .map((file) => path.basename(file, '.tsx'))
    .filter((name) => name.startsWith('Base'));

const findFilesWith = (
  files: string[],
  matcher: (content: string) => boolean,
) => files.filter((file) => matcher(readText(file)));

describe('frontend layering guardrails', () => {
  it('keeps Base components scoped to _components', () => {
    const baseNames = baseComponentNames();
    const nonComponentFiles = listFiles(SRC_ROOT)
      .filter(isSourceFile)
      .filter((file) => !file.includes(`${path.sep}_components${path.sep}`))
      .filter((file) => !isTestFile(file));

    const offenders = findFilesWith(nonComponentFiles, (content) =>
      baseNames.some((name) => content.includes(`_components/${name}`)),
    );

    expect(offenders).toEqual([]);
  });

  it('keeps flow layers from importing runtime _components', () => {
    const flowFiles = listFiles(FLOWS_DIR).filter(isSourceFile);
    const offenders = findFilesWith(flowFiles, (content) =>
      /import\s+(?!type)[^;]*['_"][^'"]*\/_components\//.test(
        content.replace(/\s+/g, ' '),
      ),
    );

    expect(offenders).toEqual([]);
  });

  it('avoids setter-style props in leaf components', () => {
    const componentFiles = listFiles(COMPONENTS_DIR).filter(isSourceFile);
    const offenders = findFilesWith(componentFiles, (content) =>
      /\bset[A-Z][A-Za-z0-9]*\s*:/.test(content),
    );

    expect(offenders).toEqual([]);
  });

  it('avoids randomized data-testid values', () => {
    const componentFiles = listFiles(COMPONENTS_DIR).filter(isSourceFile);
    const unstableTokens = [
      'Math.random',
      'Date.now',
      'randomUUID',
      'crypto.randomUUID',
    ];

    const offenders = findFilesWith(
      componentFiles,
      (content) =>
        content.includes('data-testid') &&
        unstableTokens.some((token) => content.includes(token)),
    );

    expect(offenders).toEqual([]);
  });
});
