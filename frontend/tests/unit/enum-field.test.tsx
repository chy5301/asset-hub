import { describe, expect, it } from 'vitest';
import { act, render } from '@testing-library/react';
import { useForm, type FieldValues, type UseFormReturn } from 'react-hook-form';
import { Form } from '@/components/ui/form';
import { EnumField } from '@/features/assets/form/field-controls/enum-field';
import type { FieldDef } from '@/features/assets/form/types';

// 注意（issue #39）：编辑页「空值挂载 → form.reset 程序化写值」的时序回显 bug
// 只在真实浏览器复现 —— jsdom 的 React 协调会同步重渲染触发器子树，把 bug 抹平，
// 故本层无法作为该 bug 的回归守卫。真正的回归守卫在 e2e（specs/13-edit-select-enum-reflect）。
// 这里守的是组件契约：受控值渲染到触发器 / 空值显示占位符 / radio 分支回显。

// 选项数 > 4 → 走 Select 渲染（ENUM_INLINE_THRESHOLD = 4）
const SELECT_DEF: FieldDef = {
  key: 'form_factor',
  label: '机箱形态',
  type: 'enum',
  options: ['塔式', '机架', '迷你', '刀片', '一体机'],
};

// 选项数 ≤ 4 → 走 RadioGroup（对照组）
const RADIO_DEF: FieldDef = {
  key: 'network_policy',
  label: '联网策略',
  type: 'enum',
  options: ['内网', '公网', '隔离'],
};

function Harness({
  def,
  onMethods,
}: {
  def: FieldDef;
  onMethods?: (m: UseFormReturn<FieldValues>) => void;
}) {
  const methods = useForm<FieldValues>({
    defaultValues: { custom_data: { [def.key]: '' } },
  });
  onMethods?.(methods);
  return (
    <Form {...methods}>
      <EnumField def={def} control={methods.control} />
    </Form>
  );
}

describe('EnumField 渲染契约', () => {
  it('Select 渲染（选项>4）：触发器文字反映受控值', async () => {
    let methods!: UseFormReturn<FieldValues>;
    render(<Harness def={SELECT_DEF} onMethods={(m) => (methods = m)} />);

    await act(async () => {
      methods.reset({ custom_data: { form_factor: '塔式' } });
    });

    const trigger = document.getElementById('field-form_factor');
    expect(trigger?.textContent).toContain('塔式');
  });

  it('Select 渲染：空值时触发器显示占位符', () => {
    render(<Harness def={SELECT_DEF} />);

    const trigger = document.getElementById('field-form_factor');
    expect(trigger?.textContent).toContain('请选择');
  });

  it('RadioGroup 渲染（选项≤4）：勾选态反映受控值', async () => {
    let methods!: UseFormReturn<FieldValues>;
    render(<Harness def={RADIO_DEF} onMethods={(m) => (methods = m)} />);

    await act(async () => {
      methods.reset({ custom_data: { network_policy: '公网' } });
    });

    const checked = document.querySelector('[role="radio"][data-state="checked"]');
    expect(checked?.getAttribute('value')).toBe('公网');
  });
});
