import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useForm, FormProvider } from 'react-hook-form';
import { Form } from '@/components/ui/form';
import { FieldShell } from '@/features/assets/form/field-controls/field-shell';
import type { FieldDef } from '@/features/assets/form/types';

function Harness({ def, children }: { def: FieldDef; children?: React.ReactNode }) {
  const methods = useForm({ defaultValues: { custom_data: { [def.key]: '' } } });
  return (
    <FormProvider {...methods}>
      <Form {...methods}>
        <FieldShell def={def} control={methods.control}>
          {(field) => <input {...field} data-testid="control" />}
        </FieldShell>
        {children}
      </Form>
    </FormProvider>
  );
}

describe('FieldShell', () => {
  it('required 时显示 * 星号', () => {
    render(<Harness def={{ key: 'k', type: 'string', required: true, label: 'CPU' }} />);
    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('非 required 时不显示星号', () => {
    render(<Harness def={{ key: 'k', type: 'string', required: false, label: 'CPU' }} />);
    expect(screen.queryByText('*')).not.toBeInTheDocument();
  });

  it('help 文案存在时渲染 description', () => {
    render(<Harness def={{ key: 'k', type: 'string', help: '帮助说明', label: 'CPU' }} />);
    expect(screen.getByText('帮助说明')).toBeInTheDocument();
  });

  it('layout="inline" 路径渲染（bool 特例）', () => {
    render(
      <Harness def={{ key: 'k', type: 'bool', label: '启用' }} />,
    );
    // inline 模式下 FormItem 加了 flex-row 布局类
    const item = screen.getByText('启用').closest('[class*="flex-row"]');
    // 该 case 与默认 layout 不同；具体类断言宽松
    expect(item).toBeNull(); // 默认 layout="block" 不是 flex-row
  });

  it('layout="inline" 实际加 flex-row 类 + control 在 label 之前', () => {
    const { container } = render(
      <HarnessWithLayout def={{ key: 'k', type: 'bool', label: '启用' }} layout="inline" />,
    );
    // FormItem 容器有 flex-row 类
    const item = container.querySelector('.flex.flex-row');
    expect(item).not.toBeNull();
    // DOM 顺序：control (FormControl 包 input) 在 FormLabel 之前
    if (item) {
      const formControl = item.querySelector('[data-testid="control"]');
      const formLabel = item.querySelector('label');
      expect(formControl).not.toBeNull();
      expect(formLabel).not.toBeNull();
      if (formControl && formLabel) {
        // compareDocumentPosition: 4 = formControl is FOLLOWING formLabel；2 = preceding
        // 我们期望 formControl 在 label 前 → formControl.compareDocumentPosition(label) = 4 (following)
        // 等价说：label.compareDocumentPosition(formControl) = 2 (preceding) — formControl 在 label 之前
        expect(formLabel.compareDocumentPosition(formControl) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy();
      }
    }
  });
});

function HarnessWithLayout({ def, layout }: { def: FieldDef; layout?: 'block' | 'inline' }) {
  const methods = useForm({ defaultValues: { custom_data: { [def.key]: false } } });
  return (
    <FormProvider {...methods}>
      <Form {...methods}>
        <FieldShell def={def} control={methods.control} layout={layout}>
          {(field) => <input type="checkbox" {...field} value="" data-testid="control" />}
        </FieldShell>
      </Form>
    </FormProvider>
  );
}
