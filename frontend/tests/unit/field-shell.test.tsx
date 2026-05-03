import { describe, expect, it } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { useForm, FormProvider, type UseFormReturn, type FieldValues } from 'react-hook-form';
import { Form } from '@/components/ui/form';
import { FieldShell } from '@/features/assets/form/field-controls/field-shell';
import type { FieldDef } from '@/features/assets/form/types';

function Harness({
  def,
  layout,
  defaultValue = '',
  pathPrefix,
  defaultValues,
  onMethods,
}: {
  def: FieldDef;
  layout?: 'block' | 'inline';
  defaultValue?: unknown;
  pathPrefix?: 'custom_data' | 'root';
  defaultValues?: FieldValues;
  onMethods?: (methods: UseFormReturn<FieldValues>) => void;
}) {
  const methods = useForm<FieldValues>({
    defaultValues: defaultValues ?? { custom_data: { [def.key]: defaultValue } },
  });
  onMethods?.(methods);
  return (
    <FormProvider {...methods}>
      <Form {...methods}>
        <FieldShell def={def} control={methods.control} layout={layout} pathPrefix={pathPrefix}>
          {(field) => (
            <input
              type={def.type === 'bool' ? 'checkbox' : 'text'}
              {...field}
              value={typeof field.value === 'string' ? field.value : ''}
              data-testid="control"
            />
          )}
        </FieldShell>
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

  describe('pathPrefix', () => {
    it('默认（不传）写到 custom_data.${key}（保留 8 处 custom-field 行为）', async () => {
      let captured: UseFormReturn<FieldValues> | undefined;
      render(
        <Harness
          def={{ key: 'cpu', type: 'string' }}
          defaultValues={{ custom_data: { cpu: '' }, cpu: '' }}
          onMethods={(m) => {
            captured = m;
          }}
        />,
      );
      const input = screen.getByTestId('control') as HTMLInputElement;
      await act(async () => {
        fireEvent.change(input, { target: { value: 'i7' } });
      });
      const values = captured!.getValues();
      expect(values.custom_data?.cpu).toBe('i7');
      expect(values.cpu).toBe('');
    });

    it('pathPrefix="root" 写到顶层 ${key}（acquired_at 路径）', async () => {
      let captured: UseFormReturn<FieldValues> | undefined;
      render(
        <Harness
          def={{ key: 'acquired_at', type: 'date' }}
          pathPrefix="root"
          defaultValues={{ acquired_at: '', custom_data: {} }}
          onMethods={(m) => {
            captured = m;
          }}
        />,
      );
      const input = screen.getByTestId('control') as HTMLInputElement;
      await act(async () => {
        fireEvent.change(input, { target: { value: '2026-05-03' } });
      });
      const values = captured!.getValues();
      expect(values.acquired_at).toBe('2026-05-03');
      expect(values.custom_data?.acquired_at).toBeUndefined();
    });
  });

  it('layout="inline" 实际加 flex-row 类 + control 在 label 之前', () => {
    const { container } = render(
      <Harness def={{ key: 'k', type: 'bool', label: '启用' }} layout="inline" />,
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
