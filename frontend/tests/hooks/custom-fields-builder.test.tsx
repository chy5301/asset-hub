import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { CustomFieldsBuilder } from '@/features/types/form/custom-fields-builder/builder';
import { buildTypeSchema, type CreateTypeFormValues } from '@/features/types/form/build-type-schema';

function Harness({ initial }: { initial?: Partial<CreateTypeFormValues> }) {
  const methods = useForm<CreateTypeFormValues>({
    resolver: zodResolver(buildTypeSchema({ mode: 'edit' })),
    defaultValues: {
      name: 'X',
      description: '',
      custom_fields: [],
      ...initial,
    },
  });
  return (
    <FormProvider {...methods}>
      <CustomFieldsBuilder control={methods.control} setValue={methods.setValue} errors={methods.formState.errors} />
    </FormProvider>
  );
}

describe('CustomFieldsBuilder', () => {
  it('点 "+ 添加字段" 加一张新卡', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole('button', { name: /添加字段/ }));
    expect(screen.getByText(/未命名字段/)).toBeInTheDocument();
  });

  it('删除按钮移除卡片', async () => {
    const user = userEvent.setup();
    render(<Harness initial={{ custom_fields: [{ key: 'k1', type: 'string' }] as never }} />);
    expect(screen.getByText('k1')).toBeInTheDocument();
    await user.click(screen.getByLabelText('删除字段'));
    expect(screen.queryByText('k1')).not.toBeInTheDocument();
  });

  it('空态显示虚线占位', () => {
    render(<Harness />);
    expect(screen.getByText(/添加你的第一个字段/)).toBeInTheDocument();
  });
});
