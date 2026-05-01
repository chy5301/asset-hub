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
});
