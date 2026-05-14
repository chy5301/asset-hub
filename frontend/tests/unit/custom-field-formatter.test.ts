import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import {
  type CustomFieldDef,
  formatCustomFieldValue,
} from '@/features/assets/detail/custom-field-formatter';

// 实际签名（custom-field-formatter.tsx）：
//   formatCustomFieldValue(def: CustomFieldDef, value: unknown): ReactNode
//   CustomFieldDef = { key, label, type: 'string'|'text'|'int'|'float'|'bool'|'enum'|'date', ... }
// 注意签名是 (def, value)，不是 plan 假设的 (value, def)。

const def = (overrides: Partial<CustomFieldDef> & Pick<CustomFieldDef, 'type'>): CustomFieldDef => ({
  key: 'k',
  label: 'L',
  ...overrides,
});

/** 把 ReactNode 渲染成静态 HTML，便于断言 JSX 输出。 */
const html = (node: unknown): string => renderToStaticMarkup(node as never);

describe('formatCustomFieldValue', () => {
  it('null/undefined → 占位符 — (em dash, muted)', () => {
    const out1 = html(formatCustomFieldValue(def({ type: 'string' }), null));
    const out2 = html(formatCustomFieldValue(def({ type: 'int' }), undefined));
    expect(out1).toContain('—');
    expect(out1).toContain('text-muted-foreground');
    expect(out2).toContain('—');
  });

  it('string: 返回原值', () => {
    const out = formatCustomFieldValue(def({ type: 'string' }), 'Intel i7');
    expect(out).toBe('Intel i7');
  });

  it('int: 用 Intl.NumberFormat(zh-CN) 千分位格式化', () => {
    const out = formatCustomFieldValue(def({ type: 'int' }), 1234567);
    // zh-CN 默认分组字符是普通逗号
    expect(out).toBe('1,234,567');
  });

  it('int 类型不匹配（脏数据）→ String(value) + 异常提示', () => {
    const out = html(formatCustomFieldValue(def({ type: 'int' }), 'not-a-number'));
    expect(out).toContain('not-a-number');
    expect(out).toContain('数据格式异常');
  });

  it('int + unit: 数值后追加 muted 单位（与 form NumberField 视觉一致）', () => {
    const out = html(
      formatCustomFieldValue(def({ type: 'int', unit: 'GB' }), 16),
    );
    expect(out).toContain('16');
    expect(out).toContain('GB');
    expect(out).toContain('text-muted-foreground');
  });

  it('float + unit: 同样追加单位', () => {
    const out = html(
      formatCustomFieldValue(def({ type: 'float', unit: 'Hz' }), 2.5),
    );
    expect(out).toContain('2.5');
    expect(out).toContain('Hz');
  });

  it('int + unit + null → 不渲染单位，仍显示占位符', () => {
    const out = html(
      formatCustomFieldValue(def({ type: 'int', unit: 'GB' }), null),
    );
    expect(out).toContain('—');
    expect(out).not.toContain('GB');
  });

  it('string 类型即便定义了 unit 也不渲染单位（unit 仅 int/float 生效）', () => {
    const out = formatCustomFieldValue(
      def({ type: 'string', unit: 'GB' }),
      'Lenovo',
    );
    expect(out).toBe('Lenovo');
  });

  it('bool true → Check 图标（aria-label="是"）', () => {
    const out = html(formatCustomFieldValue(def({ type: 'bool' }), true));
    expect(out).toContain('aria-label="是"');
  });

  it('bool false → X 图标（aria-label="否"）', () => {
    const out = html(formatCustomFieldValue(def({ type: 'bool' }), false));
    expect(out).toContain('aria-label="否"');
  });

  it('date: 用 formatDate 渲染成 yyyy-MM-dd 的 <time>', () => {
    const out = html(formatCustomFieldValue(def({ type: 'date' }), '2025-04-26T10:30:00Z'));
    expect(out).toContain('<time');
    expect(out).toContain('2025-04-26');
  });

  it('enum: 转成字符串展示', () => {
    const out = formatCustomFieldValue(
      def({ type: 'enum', options: ['A', 'B'] }),
      'B',
    );
    expect(out).toBe('B');
  });
});
